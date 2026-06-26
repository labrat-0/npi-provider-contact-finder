"""Integration test: website scrape -> email filter -> MX verify -> billing.

Stubs the HTTP fetch so it's deterministic, but uses a real MX lookup against a
known-good domain (harvard.edu) and a known-bad one, exercising the full path
that produces billable email events. Run with:
    python -m tests.test_enrichment_pipeline
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.billing import events_for_record  # noqa: E402
from src.enrichment import enrich_provider_website  # noqa: E402
from src.utils import RateLimiter  # noqa: E402


class _StubResponse:
    def __init__(self, text: str, url: str):
        self.status_code = 200
        self.text = text
        self.headers = {"content-type": "text/html; charset=utf-8"}
        self.url = url


class _StubClient:
    """Minimal stand-in for httpx.AsyncClient returning fixed HTML."""

    def __init__(self, html: str, url: str):
        self._html = html
        self._url = url

    async def get(self, url, **kwargs):
        return _StubResponse(self._html, self._url)


# Org record (no first/last) so the provider-name filter keeps generic mailboxes.
# One real-MX domain (harvard.edu) and one junk domain that must NOT verify.
HTML = """
<html><body>
  <a href="mailto:info@harvard.edu">email us</a>
  <p>billing: billing@nonexistent-zzz-12345qwerty.com</p>
</body></html>
"""


async def _run():
    client = _StubClient(HTML, "https://harvardmedicine.example/contact")
    rl = RateLimiter(interval=0.0)
    enrichment = await enrich_provider_website(
        website_url="https://harvardmedicine.example/contact",
        client=client,
        rate_limiter=rl,
        timeout=5,
        enable_social=False,
        first_name="",
        last_name="",  # org record -> keep generic mailboxes
    )

    emails = set(enrichment.emails)
    verified = set(enrichment.verified_emails)
    assert "info@harvard.edu" in emails, f"expected harvard email, got {emails}"
    assert "info@harvard.edu" in verified, f"harvard should MX-verify, got {verified}"
    assert "billing@nonexistent-zzz-12345qwerty.com" not in verified, (
        f"junk domain must not verify, got {verified}"
    )

    record = {"contact_enrichment": enrichment.model_dump()}
    events = events_for_record(record)
    assert "verified-email" in events, f"expected verified-email event, got {events}"
    assert "email-found" not in events, "verified email must replace email-found"

    print("emails:", sorted(emails))
    print("verified:", sorted(verified))
    print("billing events:", events)
    print("PASS")


def test_pipeline():
    asyncio.run(_run())


if __name__ == "__main__":
    asyncio.run(_run())
