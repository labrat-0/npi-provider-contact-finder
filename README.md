# NPI Provider Contact Finder

Find doctor emails, practice websites, and social media profiles from the NPPES NPI Registry. No API key required.

Search 6+ million US healthcare providers by name, specialty, or organization — then enrich each result with email addresses, LinkedIn profiles, and practice contact details scraped directly from provider websites. Replace $50K+/year databases like IQVIA and Definitive Healthcare with pay-per-use pricing. Data comes from the official NPPES API (daily updates), not month-old 4GB file dumps.

---

## Two Featured Workflows

### Batch Search by Specialty or Name

Build a territory list in one run. Pass a list of specialties (or last names, or org names) and the actor runs each search, then deduplicates results by NPI number across all queries.

**Example: Pull all cardiologists, oncologists, and neurologists in Texas**

```json
{
    "mode": "search_by_specialty",
    "searchQueriesList": ["Cardiology", "Oncology", "Neurology"],
    "state": "TX",
    "maxResults": 500,
    "enableEmailEnrichment": true
}
```

Each specialty runs as a separate NPPES search. Results are merged and deduped by NPI number. One run, one dataset, no manual merging.

**Example: Search by provider last name**

```json
{
    "mode": "search_providers",
    "searchQueriesList": ["Smith", "Jones", "Patel"],
    "state": "CA",
    "maxResults": 200
}
```

`searchQueriesList` works with `search_providers`, `search_organizations`, and `search_by_specialty` modes. If provided, it takes precedence over the single `query` field.

---

### Bulk Enrich by NPI Number

Already have a list of NPI numbers? Skip the search and go straight to enrichment.

**Path A — Small list: paste directly as a JSON array**

```json
{
    "mode": "bulk_lookup",
    "npiNumbers": ["1871538041", "1932102168", "1245319599"],
    "enableEmailEnrichment": true,
    "enableSocialMediaEnrichment": true
}
```

**Path B — Large list: upload a CSV via Apify Key-Value Store**

1. Go to **Apify Console → Storage → Key-Value Stores**
2. Click **+ Create new store** and give it a name
3. Click **+ Add record** → upload your `.csv` file
4. Find your file in the store → click the **link icon** to copy the direct URL
   > The URL must start with `api.apify.com` — **not** `console.apify.com`. The console URL is a web page and will not work as a file download.
5. Set `mode` to `bulk_lookup`, paste the URL into the `npiFile` field, and run

**CSV format** — use a column named `npi`, `npi_number`, or `NPI`, or list one NPI per row:

```
npi
1871538041
1932102168
1245319599
```

All enrichment options (email, LinkedIn, social media) work the same in bulk mode.

---

## Input Reference

**Search**

| Field | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `search_providers` | `search_providers`, `get_provider`, `search_organizations`, `search_by_specialty`, `bulk_lookup` |
| `query` | string | — | Single search term. Last name for `search_providers`, org name for `search_organizations`, specialty for `search_by_specialty`. |
| `searchQueriesList` | array | — | Run multiple searches in one go, deduped by NPI number. Takes precedence over `query`. Works with search modes only. |
| `npiNumber` | string | — | 10-digit NPI for direct lookup (`get_provider` mode). |
| `npiNumbers` | array | — | JSON array of NPI numbers (`bulk_lookup` mode). |
| `npiFile` | string | — | URL to a CSV of NPI numbers (`bulk_lookup` mode). Must be an `api.apify.com` URL from Key-Value Store. |
| `firstName` | string | — | Provider first name filter. |
| `lastName` | string | — | Provider last name filter. |
| `organizationName` | string | — | Organization name (`search_organizations` mode). |
| `taxonomyDescription` | string | — | Specialty or taxonomy description (`search_by_specialty` mode). |

**Location**

| Field | Type | Default | Description |
|---|---|---|---|
| `city` | string | — | Filter by city. |
| `state` | string | — | Two-letter state code (e.g. `CA`, `NY`, `TX`). |
| `postalCode` | string | — | ZIP/postal code filter. |
| `countryCode` | string | — | Two-letter country code. Defaults to `US`. |
| `enumerationType` | string | — | `NPI-1` (individual providers) or `NPI-2` (organizations). |

**Output**

| Field | Type | Default | Description |
|---|---|---|---|
| `maxResults` | integer | `100` | Max providers to return (1–1000). Free tier: 25 per run. |

**Advanced**

| Field | Type | Default | Description |
|---|---|---|---|
| `requestIntervalSecs` | number | `0.5` | Seconds between NPPES API requests. |
| `timeoutSecs` | integer | `30` | HTTP timeout per request (seconds). |
| `maxRetries` | integer | `5` | Max retry attempts on failed requests. |

**Enrichment**

| Field | Type | Default | Description |
|---|---|---|---|
| `enableEmailEnrichment` | boolean | `false` | Scrape practice websites for email addresses (office, billing, general). |
| `enableLinkedInEnrichment` | boolean | `false` | Search for provider LinkedIn profiles. |
| `enableSocialMediaEnrichment` | boolean | `false` | Extract Facebook, Twitter, Instagram, Healthgrades, Vitals, and Zocdoc links. |
| `emailEnrichmentTimeout` | integer | `10` | Timeout per website scrape (seconds). Lower = faster, may miss some emails. |

---

## FAQ

**What is an NPI number?**
A National Provider Identifier — a unique 10-digit ID assigned to every licensed US healthcare provider by CMS. There are over 6 million active NPIs in the registry covering physicians, nurses, dentists, therapists, and healthcare organizations.

**Is this free to use?**
The first 25 results per run are free. Subscribe to the actor for unlimited results (up to 1,000 per run).

**How does email enrichment work?**
The actor searches for the provider's practice website via DuckDuckGo, then scrapes that site for email addresses, classifying them as office, billing, or general contact. It also extracts any social media links found on the page. Success depends on whether the practice has a publicly accessible website.

**What's the difference between `npiNumbers` and `npiFile`?**
`npiNumbers` is for small lists — paste up to a few hundred NPIs directly as a JSON array. `npiFile` is for large lists — upload a CSV to Apify Key-Value Store and provide the download URL.

**Why does `npiFile` need an `api.apify.com` URL?**
`console.apify.com` URLs load a web page in your browser. The actor needs a direct file download URL to read your CSV. Always use the link icon in Key-Value Store to copy the `api.apify.com` URL, not the browser address bar.

**How fresh is the data?**
The actor queries the live NPPES API directly, which CMS updates daily. You get current provider data, not a static database snapshot.
