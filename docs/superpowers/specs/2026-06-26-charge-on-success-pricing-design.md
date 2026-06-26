# Charge-on-Success Pricing Model — Design Spec

**Date:** 2026-06-26

---

## Goal

Make the Actor's monetization **honest and bleed-proof**: the customer is charged
only for values that actually appear in their output, and no run can cost the
developer more than it earns — without taking the Actor offline.

---

## Context: the margin problem

The Actor is monetized **pay-per-event** with "User pays platform usage costs:
**No**" — meaning the developer absorbs all platform usage (compute + proxy).

The Actor previously charged a **flat per-result price** for every dataset item.
Contact enrichment, however, runs a developer-paid web search (Apify GOOGLE_SERP
proxy) per provider, whose cost can exceed the flat per-result price. Once
enrichment was working, enriched runs became unprofitable.

**Root cause:** a flat per-result price while enrichment fires an unbounded,
developer-paid web search per provider. Every enriched result can lose money, and
volume makes it worse.

Interim stopgaps (shipped, see git history): free-tier enrichment gate, a
per-run enrichment cap (`maxEnrichmentResults`, default 50), an org/location SERP
dedup cache, and finally a global kill-switch (`ENRICHMENT_DISABLED`) plus
Apify maintenance to stop the bleed entirely.

---

## Design

### 1. Charge-on-success pay-per-event

Replace the flat dataset-item charge with named events that fire **only when the
value is present** in the written record. `src/billing.py::events_for_record()`
is the single source of truth; `src/main.py::_push_and_charge()` awaits
`Actor.charge()` per event and respects the customer's max-charge budget
(`event_charge_limit_reached` stops the run).

| Event id | Fires when | Price |
|----------|-----------|-------|
| `provider-record` | any record returned | $0.001 |
| `phone-found` | record has a phone (NPPES `telephone_number`) | $0.003 |
| `email-found` | record has ≥1 usable email, none verified | $0.012 |
| `verified-email` | ≥1 email passed MX check (replaces `email-found`) | $0.020 |
| `apify-actor-start` | per run | $0.01 |

Event ids MUST match the Apify Console exactly. Keep platform-usage = No.

**Why it can't bleed:** `provider-record` + `phone-found` come from free NPPES
base data (no search), so they are profitable with zero search cost. Email events
are priced above their amortized search cost (search fires on attempts, so the
success price must cover the miss rate), so each is individually margin-positive.

### 2. Skip-SERP waterfall

`src/enrichment.py` resolves a practice website cheapest-first; the paid Google
SERP is the last resort (capped by `maxEnrichmentResults`):

1. NPPES `endpoints`/website field (free).
2. Per-run `(name, city, state)` dedup cache (free).
3. **Org-domain guess** — derive a domain from the org name and fetch it directly
   (no proxy) (`_guess_practice_domain`).
4. Paid Google SERP (`_discover_practice_website`), last resort.

### 3. Email verification

`_verify_emails` runs an MX-record check (dnspython, DNS-only, no SMTP) on each
kept email's domain. Verified addresses populate
`ContactEnrichment.verified_emails`, which selects `verified-email` vs
`email-found` in billing.

### 4. `personalEmailsOnly` input

Optional. When set, keeps only emails whose localpart contains the provider's
first/last name (≥3 chars), dropping generic role mailboxes (`info@`, `billing@`)
and domain-only matches. For direct named outreach. No personal email → no email
charge.

### 5. LinkedIn removed

The dedicated paid LinkedIn profile search (a second SERP per provider) was
removed; it could not be priced profitably. A LinkedIn URL found for free in the
scraped website HTML is still returned, unbilled.

---

## Rollout

The Actor stays on **maintenance** with `ENRICHMENT_DISABLED = True` until:

1. The 5 events above are created in the Apify Console (starts the ~2-week
   price-activation clock); old `apify-default-dataset-item` removed.
2. Once prices are live: set `ENRICHMENT_DISABLED = False`, `apify push`, take off
   maintenance.

Base records + phone bill immediately and profitably; enrichment events activate
with the price change.

---

## Verification

- `tests/test_billing.py` — event selection (9 cases).
- `tests/test_enrichment_pipeline.py` — extract → name-filter → live MX verify →
  event selection (verified vs junk domain).
- `tests/test_personal_emails.py` — personal-only filter.
- Live NPPES smoke run confirmed records carry phones and bill correctly.
- Post-deploy: Apify Insights margin positive; charge count reconciles to dataset
  rows.
