# AGENTS.md — NPI Provider Contact Finder

Orientation for AI agents working on this repo. Read this first.

## What this is

An Apify Actor that searches the CMS **NPPES NPI Registry** for US healthcare
providers and optionally enriches them with contact data (practice website,
emails, phone, social links). Python, async, built on the Apify SDK.

## Architecture map

| File | Responsibility |
|------|----------------|
| `src/main.py` | Actor entry point. Free-tier limits, the **enrichment kill-switch**, pay-per-event **charging** (`_push_and_charge`), the push/scrape loop. |
| `src/scraper.py` | `NPIProviderScraper`: NPPES API fetch, normalization, the per-run enrichment loop + `_website_cache` (per-run dedup). |
| `src/enrichment.py` | Website discovery **waterfall**, email extraction + provider-name filtering, **MX verification**, social/phone parsing. |
| `src/billing.py` | `events_for_record()` — pure mapping of a delivered record → billable events (charge-on-success). |
| `src/models.py` | `ScraperInput` (config) and the output record models. |
| `.actor/` | `actor.json`, `input_schema.json` (input UI), dataset/output schemas. |
| `tests/` | `test_billing.py`, `test_enrichment_pipeline.py`, `test_personal_emails.py`. |

## Pricing model (charge-on-success pay-per-event)

The customer is billed **only for values that appear in their output**. Event ids
in `src/billing.py` MUST match the Apify Console monetization config exactly.

| Event id | Charged when | Price |
|----------|--------------|-------|
| `provider-record` | a provider record is returned | $0.001 |
| `phone-found` | record has a phone (from NPPES — free data) | $0.003 |
| `email-found` | record has an unverified email | $0.012 |
| `verified-email` | email passed MX check (instead of `email-found`) | $0.020 |
| `apify-actor-start` | per run | $0.01 |

Keep **"User pays platform usage costs: Yes"** in the console (both Pay-Per-Event
and Usage toggles must be ON together — Apify Console couples them). With this
model the user's bill is event prices + platform costs, and every event cent is
pure developer margin. Do not reintroduce a flat per-result charge; that
combination is not sustainable (see the spec below).

## CURRENT STATE (critical — read before deploying)

- The Actor is on **maintenance** on Apify (paused).
- Enrichment is **hard-disabled**: `ENRICHMENT_DISABLED = True` in `src/main.py`
  (a cost stopgap). Runs return base provider data (records + phone) only; no
  paid web search runs.
- Pay-per-event prices were **configured in Console on 2026-06-27**:
  `provider-record=$0.001`, `phone-found=$0.003`, `email-found=$0.012`,
  `verified-email=$0.020`, `apify-actor-start=$0.01`.
  The old `apify-default-dataset-item` was removed. Prices take **~2 weeks**
  to propagate (expected live ~2026-07-11). User pays platform usage = Yes.
- All code is on `main`. Nothing has been `apify push`ed since this rework.

## Deploy sequence (next steps)

1. Prices were configured on 2026-06-27. Wait **~2 weeks** for propagation.
2. When the new prices are live (target ~2026-07-11): set
   `ENRICHMENT_DISABLED = False` in `src/main.py`.
3. `apify push` to build, then take the Actor off maintenance.
4. Watch next-day Apify Insights for positive margin; spot-check that a run's
   charge count matches its dataset rows.

## Running / testing

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # apify, httpx, pydantic, bs4, lxml, dnspython
python -m tests.test_billing
python -m tests.test_enrichment_pipeline  # uses live DNS for MX check
python -m tests.test_personal_emails
```

Charging only fires for paying users on-platform (`APIFY_IS_AT_HOME=1` +
`APIFY_USER_IS_PAYING=1`); local runs never bill. A virtualenv named
`.venv-test` may exist locally — it is gitignored; recreate from
`requirements.txt`.

## Why (full rationale)

See `docs/superpowers/specs/2026-06-26-charge-on-success-pricing-design.md` for
the margin-bleed history, root cause, and the complete design.
