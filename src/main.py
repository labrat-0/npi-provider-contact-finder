from __future__ import annotations

import csv
import io
import logging
import os

import httpx
from apify import Actor

from .models import ScraperInput, ScrapingMode
from .scraper import NPIProviderScraper
from .utils import RateLimiter

logger = logging.getLogger(__name__)

FREE_TIER_LIMIT = 25


async def main() -> None:
    async with Actor:
        raw_input = await Actor.get_input() or {}
        config = ScraperInput.from_actor_input(raw_input)

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

        max_results = config.max_results
        if not is_paying and os.environ.get("APIFY_IS_AT_HOME") == "1":
            max_results = min(max_results, FREE_TIER_LIMIT)
            Actor.log.info(
                f"Free tier: limited to {FREE_TIER_LIMIT} results. "
                "Subscribe to the actor for unlimited results."
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

        async with httpx.AsyncClient() as client:
            rate_limiter = RateLimiter(interval=config.request_interval_secs)
            scraper = NPIProviderScraper(client, rate_limiter, config)

            count = state["scraped"]
            batch: list[dict] = []
            batch_size = 25

            scrape_iter = (
                scraper.scrape_bulk()
                if config.mode == ScrapingMode.BULK_LOOKUP
                else scraper.scrape()
            )

            try:
                async for item in scrape_iter:
                    if count >= max_results:
                        break

                    batch.append(item)
                    count += 1
                    state["scraped"] = count

                    if len(batch) >= batch_size:
                        await Actor.push_data(batch)
                        batch = []
                        await Actor.set_status_message(f"Scraped {count}/{max_results} providers")

                if batch:
                    await Actor.push_data(batch)

            except Exception as e:  # pragma: no cover - defensive
                state["failed"] += 1
                Actor.log.error(f"Scraping error: {e}")
                if batch:
                    await Actor.push_data(batch)

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
