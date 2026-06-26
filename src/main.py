from __future__ import annotations

import csv
import io
import logging
import os

import httpx
from apify import Actor

from .billing import events_for_record
from .models import ScraperInput, ScrapingMode
from .scraper import NPIProviderScraper
from .utils import RateLimiter

SEARCH_MODES = {ScrapingMode.SEARCH_PROVIDERS, ScrapingMode.SEARCH_ORGANIZATIONS, ScrapingMode.SEARCH_BY_SPECIALTY}

logger = logging.getLogger(__name__)

FREE_TIER_LIMIT = 25

# Global kill-switch for paid contact enrichment. Each enriched provider fires
# Google SERP proxy calls (~$6-13 per 1K results) that exceed current realized
# revenue, so enrichment runs at a structural loss. Disabled until enrichment is
# repriced or redesigned to skip the paid search. Flip to False to restore normal
# enrichment behavior (per-user opt-in via the enable* input flags).
ENRICHMENT_DISABLED = True


async def _push_and_charge(batch: list[dict], charging_enabled: bool) -> None:
    """Push a batch to the dataset, then charge pay-per-event events for each
    delivered record (charge-on-success). Charging only runs for paying users
    on the platform; the Apify SDK enforces the customer's max-charge budget, so
    we never over-bill. A failed individual charge is logged, not fatal."""
    if not batch:
        return
    await Actor.push_data(batch)
    if not charging_enabled:
        return
    for record in batch:
        for event in events_for_record(record):
            try:
                await Actor.charge(event)
            except Exception as e:
                Actor.log.warning(f"charge({event}) failed: {e}")


async def main() -> None:
    async with Actor:
        raw_input = await Actor.get_input() or {}
        config = ScraperInput.from_actor_input(raw_input)

        # Hard-disable all enrichment globally (cost stopgap). Overrides any
        # user input; the actor still returns full base NPI data. With these
        # flags off, the proxy setup below and the scraper's enrichment calls
        # are skipped, so no paid SERP calls are made.
        if ENRICHMENT_DISABLED and (
            config.enable_email_enrichment
            or config.enable_linkedin_enrichment
            or config.enable_social_media_enrichment
        ):
            config.enable_email_enrichment = False
            config.enable_linkedin_enrichment = False
            config.enable_social_media_enrichment = False
            Actor.log.info(
                "Contact enrichment is temporarily disabled; returning base NPI "
                "data only. No web search or proxy usage will occur this run."
            )

        # Handle CSV/JSON file upload for bulk_lookup mode
        if config.mode == ScrapingMode.BULK_LOOKUP and not config.npi_numbers:
            npi_file_url = raw_input.get("npiFile")
            if npi_file_url:
                try:
                    async with httpx.AsyncClient() as dl_client:
                        resp = await dl_client.get(npi_file_url, timeout=30)
                        resp.raise_for_status()
                        content = resp.text
                    # Try CSV first, then plain newline-delimited
                    parsed: list[str] = []
                    reader = csv.DictReader(io.StringIO(content))
                    npi_col = next(
                        (f for f in (reader.fieldnames or []) if f.strip().lower() in ("npi", "npi_number", "npi number")),
                        None,
                    )
                    if npi_col:
                        parsed = [row[npi_col].strip() for row in reader if row[npi_col].strip()]
                    else:
                        # Fallback: first column or plain list
                        for line in content.splitlines():
                            val = line.split(",")[0].strip().strip('"')
                            if val and val.lower() not in ("npi", "npi_number"):
                                parsed.append(val)
                    config.npi_numbers = [n for n in parsed if n]
                    Actor.log.info(f"Loaded {len(config.npi_numbers)} NPI numbers from uploaded file.")
                except Exception as e:
                    await Actor.fail(status_message=f"Failed to read npiFile: {e}")
                    return

        validation_error = config.validate_for_mode()
        if validation_error:
            await Actor.fail(status_message=validation_error)
            return

        is_paying = os.environ.get("APIFY_IS_AT_HOME") == "1" and os.environ.get(
            "APIFY_USER_IS_PAYING"
        ) == "1"

        # Charge pay-per-event only for paying users on the platform. Off-platform
        # (local dev) and free-tier runs never bill. The SDK enforces the
        # customer's max-charge budget.
        charging_enabled = is_paying and os.environ.get("APIFY_IS_AT_HOME") == "1"

        max_results = config.max_results
        if not is_paying and os.environ.get("APIFY_IS_AT_HOME") == "1":
            max_results = min(max_results, FREE_TIER_LIMIT)
            Actor.log.info(
                f"Free tier: limited to {FREE_TIER_LIMIT} results. "
                "Subscribe to the actor for unlimited results."
            )

            # Paid contact enrichment fires per-provider Google SERP proxy calls,
            # which cost the developer real platform usage. Free-tier runs return
            # $0 revenue, so enriching them loses money on every call. Disable all
            # enrichment for non-paying users; they still get full base NPI data.
            if (
                config.enable_email_enrichment
                or config.enable_linkedin_enrichment
                or config.enable_social_media_enrichment
            ):
                config.enable_email_enrichment = False
                config.enable_linkedin_enrichment = False
                config.enable_social_media_enrichment = False
                Actor.log.info(
                    "Contact enrichment requires a paid plan; returning base NPI "
                    "data only. Subscribe to the actor to enable email, LinkedIn, "
                    "and social enrichment."
                )

        # Override config max_results with the effective limit
        config.max_results = max_results

        Actor.log.info(
            "Starting NPI Provider Scraper | mode=%s | max_results=%s",
            config.mode.value,
            max_results,
        )

        state = await Actor.use_state(default_value={"scraped": 0, "failed": 0})

        await Actor.set_status_message("Searching NPPES NPI Registry...")

        # Build a proxied client for web search (website + LinkedIn discovery).
        # Public search endpoints now block datacenter IPs, so search must route
        # through Apify Proxy (Google SERP group by default). Falls back to a
        # direct connection when proxy is unavailable (e.g. local dev).
        search_proxy_url = None
        if config.enable_email_enrichment:
            proxy_input = raw_input.get("proxyConfiguration")
            try:
                if proxy_input:
                    proxy_cfg = await Actor.create_proxy_configuration(actor_proxy_input=proxy_input)
                else:
                    proxy_cfg = await Actor.create_proxy_configuration(groups=["GOOGLE_SERP"])
                if proxy_cfg:
                    search_proxy_url = await proxy_cfg.new_url()
            except Exception as e:
                Actor.log.warning(
                    f"Proxy configuration unavailable ({e}); web search will run "
                    "without a proxy and may be rate-limited or blocked."
                )

        async with httpx.AsyncClient() as client, httpx.AsyncClient(proxy=search_proxy_url) as search_client:
            rate_limiter = RateLimiter(interval=config.request_interval_secs)
            scraper = NPIProviderScraper(client, rate_limiter, config, search_client=search_client)

            count = state["scraped"]
            batch: list[dict] = []
            batch_size = 25

            if config.mode == ScrapingMode.BULK_LOOKUP:
                # Existing bulk path — unchanged, no dedup needed (NPIs are explicit)
                try:
                    async for item in scraper.scrape_bulk():
                        if count >= max_results:
                            break
                        batch.append(item)
                        count += 1
                        state["scraped"] = count
                        if len(batch) >= batch_size:
                            await _push_and_charge(batch, charging_enabled)
                            batch = []
                            await Actor.set_status_message(f"Scraped {count}/{max_results} providers")
                    if batch:
                        await _push_and_charge(batch, charging_enabled)
                except Exception as e:
                    state["failed"] += 1
                    Actor.log.error(f"Scraping error: {e}")
                    if batch:
                        await _push_and_charge(batch, charging_enabled)
            else:
                # Multi-query loop for search and get_provider modes
                search_queries = (
                    config.queries_list
                    if (config.mode in SEARCH_MODES and config.queries_list)
                    else ([config.query] if config.query else [""])
                )
                seen_npis: set[str] = set()

                try:
                    for query in search_queries:
                        if count >= max_results:
                            break

                        config.query = query
                        if len(search_queries) > 1:
                            Actor.log.info(f"Searching for query: {query!r}")

                        async for item in scraper.scrape():
                            if count >= max_results:
                                break

                            npi = item.get("npi_number", "")
                            if npi and npi in seen_npis:
                                continue
                            if npi:
                                seen_npis.add(npi)

                            batch.append(item)
                            count += 1
                            state["scraped"] = count

                            if len(batch) >= batch_size:
                                await _push_and_charge(batch, charging_enabled)
                                batch = []
                                await Actor.set_status_message(f"Scraped {count}/{max_results} providers")

                    if batch:
                        await _push_and_charge(batch, charging_enabled)

                except Exception as e:
                    state["failed"] += 1
                    Actor.log.error(f"Scraping error: {e}")
                    if batch:
                        await _push_and_charge(batch, charging_enabled)

        msg = f"Done. Scraped {count} providers."
        if state["failed"] > 0:
            msg += f" {state['failed']} errors encountered."
        if (
            not is_paying
            and os.environ.get("APIFY_IS_AT_HOME") == "1"
            and count >= FREE_TIER_LIMIT
        ):
            msg += (
                f" Free tier limit ({FREE_TIER_LIMIT}) reached."
                " Subscribe for unlimited results."
            )

        Actor.log.info(msg)
        await Actor.set_status_message(msg)
