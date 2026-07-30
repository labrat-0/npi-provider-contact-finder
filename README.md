# NPI Provider Contact Finder

**Generate healthcare sales leads with verified provider contact information from the official NPPES NPI Registry.**

[![Apify](https://img.shields.io/badge/Apify-available-4dff8a)](https://apify.com/labrat011/npi-provider-contact-finder)
[![NPPES](https://img.shields.io/badge/source-NPPES%20NPI%20Registry-blue)](https://npiregistry.cms.hhs.gov/)


## What This Actor Does

This actor searches the **official NPPES NPI Registry** (maintained by CMS/HHS) and returns structured healthcare provider records with verified practice contact information. It covers **6+ million individual and organizational providers** — every enrolled Medicare/Medicaid provider in the United States.

**Perfect for:**
- **Medical device sales** — find specialist contact info by location and specialty
- **Pharmaceutical outreach** — build targeted lists of prescribers
- **Healthcare marketing** — identify potential clients by practice type
- **Provider network management** — verify and enrich provider rosters
- **Market research** — analyze provider density, specialties, and distribution

---

## Features

| Feature | Description |
|---------|-------------|
| **Official NPPES data** | Direct API access to the government's NPI registry — no scraping, no third-party aggregators |
| **Multiple search modes** | Search by name, NPI number, organization, specialty, or location |
| **Batch lookups** | Upload CSV/JSON files with up to thousands of NPI numbers |
| **Bulk specialty search** | Run multiple specialty searches in one go with automatic dedup |
| **Contact enrichment** | Practice website email discovery, social media, LinkedIn profiles, and MX verification |
| **Email verification** | MX-record verification for deliverability confidence |
| **Comprehensive output** | Full NPI data: taxonomy codes, addresses, phone/fax, identifiers, endpoints |
| **Pay-per-event pricing** | Only pay for the data you use — no subscriptions, no monthly commitments |

---

## How to Use

### Quick Start

1. Open the actor on [Apify Console](https://console.apify.com/actors/labrat011/npi-provider-contact-finder)
2. Select your **search mode**
3. Enter your search criteria
4. Run! Results appear in your dataset within seconds

### Search Modes

| Mode | Description | Example |
|------|-------------|---------|
| `search_providers` | Search individual providers by name + location | Last name "Smith" in "NY" |
| `get_provider` | Look up a specific provider by NPI number | NPI `1881018208` (Mayo Clinic) |
| `search_organizations` | Find hospitals, clinics, and group practices | Organization name "Mayo Clinic" |
| `search_by_specialty` | Find providers by specialty/taxonomy | "Cardiovascular Disease" in "TX" |
| `bulk_lookup` | Upload a CSV/JSON list of NPI numbers | 500 NPIs from your CRM export |

> **Specialty values must match the NUCC taxonomy description.** The registry
> matches on the description text, so `"Cardiovascular Disease"` finds
> cardiologists while `"Cardiology"` mostly returns *pharmacists* whose taxonomy
> is "Pharmacist, Cardiology". Likewise it is `"Orthopaedic Surgery"` (British
> spelling) — `"Orthopedic Surgery"` returns nothing. A trailing wildcard works
> after two characters, e.g. `"Derm*"`.

### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | select | `search_providers` | Search mode (see above) |
| `query` | string | — | General search term (last name, org name, or specialty) |
| `searchQueriesList` | array | — | Run multiple searches in one run, auto-deduped |
| `maxResults` | number | `100` | Maximum number of results to return |
| `state` | string | — | Filter by state (2-letter code: `NY`, `CA`, `TX`) |
| `city` | string | — | Filter by city |
| `postalCode` | string | — | Filter by ZIP code |
| `enableEmailEnrichment` | bool | `false` | Enable practice website email discovery |
| `personalEmailsOnly` | bool | `false` | Keep only direct provider emails (drop role mailboxes) |

> **Free tier**: Limited to 25 results per run. Subscribe to unlock unlimited results.

---

## Pricing

This actor uses pay-per-event (PPE) pricing. You pay only for what the actor actually finds — not every provider has a phone or email, so your cost scales with how much contact data exists for your query.

| Event | Price | When Charged |
|-------|-------|-------------|
| **Actor Start** | $0.01 per run | Charged once per run |
| **Provider Record** | **$1.00 / 1K records** | Every NPPES provider record returned |
| **Phone Found** | $3.00 / 1K records | Record has a practice phone number |
| **Email Found** | $12.00 / 1K records | Email discovered from practice website |
| **Verified Email** | $20.00 / 1K records | MX-verified deliverable email address |

Platform usage (proxy/compute) is billed to your account in addition to the above.

*Prices subject to change with 14-day notice as per Apify platform policy.*
---

## Output Schema

Each provider record returns (values below are illustrative, not a real
provider; `primary_specialty` carries the full NUCC taxonomy description):

```json
{
  "npi_number": "1234567890",
  "enumeration_type": "NPI-1",
  "first_name": "Jane",
  "last_name": "Smith",
  "credential": "MD",
  "primary_specialty": "Internal Medicine, Cardiovascular Disease",
  "practice_address_city": "Rochester",
  "practice_address_state": "MN",
  "addresses": [
    {
      "address_purpose": "LOCATION",
      "telephone_number": "(555) 123-4567",
      "city": "Rochester",
      "state": "MN",
      "postal_code": "55901"
    }
  ],
  "taxonomies": [
    {
      "code": "207RC0000X",
      "description": "Cardiovascular Disease",
      "primary": true
    }
  ],
  "contact_enrichment": {
    "emails": ["jsmith@cardio.com"],
    "verified_emails": ["jsmith@cardio.com"],
    "practice_website": "https://www.rochestercardio.com",
    "linkedin_profile_url": "https://linkedin.com/in/janesmithmd"
  }
}
```

---

## Data Sources

- **NPPES NPI Registry** (CMS/HHS) — the official federal database of all healthcare providers enrolled in Medicare/Medicaid. Updated daily. [NPPES API](https://npiregistry.cms.hhs.gov/)
- **Practice websites** — ethical, non-invasive discovery of published contact information from provider practice websites
- No third-party data brokers, no resold contact lists, no gray-market data sources

---

## Enrichment Notes

Contact enrichment (email and website discovery) uses public Google search results routed through Apify's Google SERP proxy. Enrichment is opt-in (`enableEmailEnrichment: true`) and is recommended for paid users running targeted searches. Defaults to 50 enriched providers per run, adjustable up to 100,000 via the `maxEnrichmentResults` input parameter.

Free tier runs always return base NPI data without enrichment — subscribe for enriched results.

---

## Limitations

| Aspect | Detail |
|--------|--------|
| NPPES update lag | Registry reflects Medicare enrollment, not daily credentialing changes |
| Email discovery | Not guaranteed — some practices have no published contact email |
| International providers | Limited to US providers enrolled in Medicare/Medicaid |
| NPI-2 organizations | Organizational records include authorized official contacts where available |

---

## Changelog

**v2.1.0** (current)
- Re-enabled contact enrichment with MX email verification
- Pay-per-event pricing configured
- Lazy-loading enrichment dependencies for faster cold starts
- Added `.dockerignore` for leaner builds

**v2.0.0**
- Major rewrite: async httpx, Pydantic v2 models, rate-limited NPPES API
- Multi-query batch mode with automatic dedup
- Bulk CSV/JSON file upload support
- Contact enrichment with email, LinkedIn, social media discovery
- MX-verified email billing (verified-email vs email-found)

---

## Support

- [GitHub Issues](https://github.com/labrat-0/npi-provider-contact-finder/issues)
- [Apify Store Page](https://apify.com/labrat011/npi-provider-contact-finder)
- [NPPES NPI Registry](https://npiregistry.cms.hhs.gov/)
