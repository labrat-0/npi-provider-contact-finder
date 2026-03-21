# NPI Provider Contact Finder

> **Find doctor emails, practice websites, and social media profiles from the NPPES NPI Registry — no API key required. Search 6M+ US healthcare providers by name, specialty, or organization, then enrich each result with contact data.**

Replace $50K+/year databases like IQVIA and Definitive Healthcare with pay-per-use pricing. Data comes from the official NPPES API (daily updates from CMS), not month-old 4GB file dumps.

---

## 🌟 Why This Beats the Alternatives

**Live NPPES data, not static dumps.** Most competitors sell annual database exports. This actor queries the live NPPES API — updated daily by CMS — so you get current licensure status, current addresses, and current specialty classifications.

**Contact enrichment included.** NPI Registry gives you name and address. This actor goes further: it finds the practice website, scrapes for email addresses, and extracts LinkedIn, Healthgrades, Vitals, and Zocdoc links — all in one run.

**Batch search built in.** Query 10 specialties across 5 states in one run. Results are deduplicated by NPI number automatically — no spreadsheet merging, no duplicates.

**Five modes for every workflow.** Search by name, specialty, or organization. Direct NPI lookup. Bulk enrichment from a CSV. Whatever your workflow, there's a mode for it.

---

## 🎯 Use Cases

### 🏥 Medical Device & Pharma Sales Reps

Build territory lists without buying a data subscription. Search by specialty and state to get every physician in your territory with contact info, practice address, and phone — ready to import into your CRM.

**Example: All interventional cardiologists and cardiac surgeons in Georgia and Florida**

```json
{
    "mode": "search_by_specialty",
    "searchQueriesList": ["Interventional Cardiology", "Cardiac Surgery"],
    "state": "GA",
    "maxResults": 500,
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true
}
```

Run twice — once for GA, once for FL. Or use two separate Actor runs.

**Example: Target orthopedic surgeons in a ZIP code cluster**

```json
{
    "mode": "search_by_specialty",
    "query": "Orthopedic Surgery",
    "city": "Houston",
    "state": "TX",
    "maxResults": 200,
    "enableEmailEnrichment": true,
    "enableSocialMediaEnrichment": true
}
```

---

### 🧪 Clinical Research Organizations (CROs)

Find principal investigators for clinical trials by specialty, location, and institution. Skip the manual CLINICALTRIALS.GOV → Google → LinkedIn chain.

**Example: Oncologists at academic medical centers in specific states**

```json
{
    "mode": "search_by_specialty",
    "searchQueriesList": ["Medical Oncology", "Hematology & Oncology", "Radiation Oncology"],
    "state": "MA",
    "enumerationType": "NPI-1",
    "maxResults": 300,
    "enableEmailEnrichment": true
}
```

**Example: Bulk enrich your existing investigator list**

Already have a list of NPI numbers from a previous study? Skip the search entirely:

```json
{
    "mode": "bulk_lookup",
    "npiNumbers": ["1871538041", "1932102168", "1245319599", "1508943127"],
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true
}
```

---

### 📊 Healthcare Marketing Agencies

Build segmented lists for digital campaigns. Target by specialty, geography, and organization type. Get LinkedIn profiles for account-based targeting on social platforms.

**Example: Primary care physicians in the Northeast for a telehealth campaign**

```json
{
    "mode": "search_by_specialty",
    "searchQueriesList": ["Family Medicine", "Internal Medicine", "General Practice"],
    "state": "NY",
    "maxResults": 1000,
    "enableLinkedInEnrichment": true,
    "enableSocialMediaEnrichment": true
}
```

**Example: Hospital systems and health networks in a metro area**

```json
{
    "mode": "search_organizations",
    "query": "Medical Center",
    "city": "Chicago",
    "state": "IL",
    "enumerationType": "NPI-2",
    "maxResults": 100,
    "enableEmailEnrichment": true
}
```

---

### 🤖 AI Agents & Automated Pipelines

This actor is agent-ready. Structured JSON output with consistent schemas makes it a clean data source for AI workflows:

- **LLM pipelines**: Wire as a tool call — your agent queries for providers matching criteria, gets back structured records, and reasons over them
- **CRM automation**: Trigger this actor from a Zapier/Make workflow to enrich new leads automatically
- **RAG knowledge base**: Index provider records into a vector store for semantic retrieval
- **Lead scoring agents**: Combine specialty, practice size (inferred from organization type), and enriched contact data for automated scoring

**Example: Agent-friendly query — specific providers by last name across states**

```json
{
    "mode": "search_providers",
    "searchQueriesList": ["Patel", "Kumar", "Sharma"],
    "state": "NJ",
    "maxResults": 200,
    "enableEmailEnrichment": true
}
```

---

### 🔬 Healthcare Data Scientists

Access structured provider data without managing large NPPES file downloads (the full NPPES export is 4GB+). Pull exactly what you need via API.

**Example: Map all licensed psychiatrists by state for a mental health access study**

```json
{
    "mode": "search_by_specialty",
    "query": "Psychiatry",
    "enumerationType": "NPI-1",
    "maxResults": 1000
}
```

**Example: Get full record for a specific NPI number**

```json
{
    "mode": "get_provider",
    "npiNumber": "1871538041",
    "enableEmailEnrichment": true,
    "enableSocialMediaEnrichment": true
}
```

---

## 📦 What You Get

Each output record is a `ProviderRecord` with the following data:

**Core Identity**

| Field | Description |
|---|---|
| `npi_number` | 10-digit NPI identifier |
| `enumeration_type` | `NPI-1` (individual) or `NPI-2` (organization) |
| `first_name`, `last_name` | Provider name |
| `credential` | Degrees and credentials (MD, DO, NP, PA, etc.) |
| `organization_name` | Organization name (NPI-2 records) |
| `status` | Active / Deactivated |
| `primary_specialty` | Top taxonomy description (convenience field) |

**Address & Contact**

| Field | Description |
|---|---|
| `addresses` | Array of MAILING and LOCATION addresses with phone and fax |
| `practice_address_city` | City from primary practice location (convenience field) |
| `practice_address_state` | State from primary practice location (convenience field) |

**Taxonomies & Specialties**

| Field | Description |
|---|---|
| `taxonomies` | Full array of specialties with code, description, license, state, and primary flag |
| `identifiers` | DEA numbers, state license numbers, UPIN, and other identifiers |

**Enrichment (optional)**

| Field | Description |
|---|---|
| `contact_enrichment.emails` | All email addresses found on practice website |
| `contact_enrichment.primary_email` | Best contact email |
| `contact_enrichment.office_email` | Office/scheduling email |
| `contact_enrichment.billing_email` | Billing department email |
| `contact_enrichment.practice_website` | Practice website URL |
| `contact_enrichment.linkedin_profile_url` | Provider LinkedIn URL |
| `contact_enrichment.healthgrades_url` | Healthgrades profile |
| `contact_enrichment.vitals_url` | Vitals.com profile |
| `contact_enrichment.zocdoc_url` | Zocdoc booking page |
| `contact_enrichment.facebook_url` | Practice Facebook page |
| `contact_enrichment.npi_registry_url` | Direct NPI Registry link |

---

## 🔀 Two Batch Workflows

### Batch Search by Specialty or Name

Build a territory list in one run. Pass a list of specialties (or last names, or org names) via `searchQueriesList` and the actor runs each search, then deduplicates results by NPI number across all queries.

**Example: Three specialties, one run**

```json
{
    "mode": "search_by_specialty",
    "searchQueriesList": ["Cardiology", "Oncology", "Neurology"],
    "state": "TX",
    "maxResults": 500,
    "enableEmailEnrichment": true
}
```

`searchQueriesList` works with `search_providers`, `search_organizations`, and `search_by_specialty` modes. Takes precedence over the single `query` field.

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

All enrichment options work the same in bulk mode.

---

## ⚙️ Input Reference

**Mode & Search**

| Field | Type | Default | Description |
|---|---|---|---|
| `mode` | string | `search_providers` | `search_providers`, `get_provider`, `search_organizations`, `search_by_specialty`, `bulk_lookup` |
| `query` | string | — | Single search term: last name (search_providers), org name (search_organizations), specialty (search_by_specialty). |
| `searchQueriesList` | array | — | Run multiple searches in one go, deduped by NPI. Takes precedence over `query`. |
| `npiNumber` | string | — | 10-digit NPI for direct lookup (`get_provider` mode). |
| `npiNumbers` | array | — | JSON array of NPI numbers (`bulk_lookup` mode). |
| `npiFile` | string | — | URL to a CSV of NPI numbers (`bulk_lookup` mode). Must be an `api.apify.com` URL from Key-Value Store. |
| `firstName` | string | — | Provider first name filter. |
| `lastName` | string | — | Provider last name filter. |
| `organizationName` | string | — | Organization name (`search_organizations` mode). |
| `taxonomyDescription` | string | — | Specialty or taxonomy description (`search_by_specialty` mode). |

**Location Filters**

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

**Contact Enrichment**

| Field | Type | Default | Description |
|---|---|---|---|
| `enableEmailEnrichment` | boolean | `false` | Scrape practice websites for email addresses (office, billing, general). |
| `enableLinkedInEnrichment` | boolean | `false` | Search for provider LinkedIn profiles. |
| `enableSocialMediaEnrichment` | boolean | `false` | Extract Facebook, Twitter, Instagram, Healthgrades, Vitals, and Zocdoc links. |
| `emailEnrichmentTimeout` | integer | `10` | Timeout per website scrape (seconds). Lower = faster, may miss some emails. |

**Advanced**

| Field | Type | Default | Description |
|---|---|---|---|
| `requestIntervalSecs` | number | `0.5` | Seconds between NPPES API requests. |
| `timeoutSecs` | integer | `30` | HTTP timeout per request (seconds). |
| `maxRetries` | integer | `5` | Max retry attempts on failed requests. |

---

## ❓ FAQ

**What is an NPI number?**
A National Provider Identifier — a unique 10-digit ID assigned to every licensed US healthcare provider by CMS. Over 6 million active NPIs in the registry cover physicians, nurses, dentists, therapists, and healthcare organizations.

**Is this free to use?**
The first 25 results per run are free. Subscribe to the actor for unlimited results (up to 1,000 per run).

**How does email enrichment work?**
The actor searches for the provider's practice website via DuckDuckGo, then scrapes that site for email addresses, classifying them as office, billing, or general contact. It also extracts any social media links found on the page. Success depends on whether the practice has a publicly accessible website.

**How fresh is the data?**
The actor queries the live NPPES API directly, which CMS updates daily. You get current provider data, not a static database snapshot.

**What's the difference between `npiNumbers` and `npiFile`?**
`npiNumbers` is for small lists — paste up to a few hundred NPIs directly as a JSON array. `npiFile` is for large lists — upload a CSV to Apify Key-Value Store and provide the download URL.

**Why does `npiFile` need an `api.apify.com` URL?**
`console.apify.com` URLs load a web page in your browser. The actor needs a direct file download URL to read your CSV. Always use the link icon in Key-Value Store to copy the `api.apify.com` URL, not the browser address bar.

**What enrichment hit rate should I expect?**
Email enrichment depends on whether the practice has a public website. Solo practitioners typically have lower hit rates than group practices. Expect 40–70% email hit rate for individual providers, higher for organizations. LinkedIn enrichment works best for physicians at academic institutions and large health systems.

**Can I search by taxonomy code instead of specialty name?**
The `taxonomyDescription` field accepts text descriptions like "Cardiology" or "Orthopedic Surgery". For exact taxonomy code lookups, use the `query` field in `search_by_specialty` mode with the code directly (e.g., `207RC0000X` for Cardiovascular Disease).
