# AGENTS.md — NPI Provider Contact Finder

Orientation for AI agents working on this repo. Read this first.

## What this is

An Apify Actor that searches the CMS **NPPES NPI Registry** for US healthcare
providers and optionally enriches them with contact data (practice website,
emails, phone, social links). Python, async, built on the Apify SDK.

## Architecture map

| File | Responsibility |
|------|----------------|
| `src/main.py` | Actor entry point. Free-tier limits, pay-per-event charging, the push/scrape loop. |
| `src/scraper.py` | `NPIProviderScraper`: NPPES API fetch, normalization, the per-run enrichment loop. |
| `src/enrichment.py` | Website discovery waterfall, email extraction + provider-name filtering, MX verification, social/phone parsing. |
| `src/billing.py` | `events_for_record()` — mapping of a delivered record to billable events. |
| `src/models.py` | `ScraperInput` (config) and output record models (Pydantic v2). |
| `.actor/` | `actor.json`, `input_schema.json` (input UI), dataset/output schemas. |
| `tests/` | Unit and integration tests. |

## Running / testing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m tests.test_billing
python -m tests.test_enrichment_pipeline
python -m tests.test_personal_emails
```

Charging only fires on-platform (`APIFY_IS_AT_HOME=1` + `APIFY_USER_IS_PAYING=1`);
local runs never bill.

## Pricing

Pay-per-event. Event IDs and prices are configured in the Apify Console
Monetization tab. See `src/billing.py` for event definitions.