# NPI Provider Contact Finder v2.1.0 — Design Spec

**Date:** 2026-03-20
**Version bump:** 2.0.0 → 2.1.0

---

## Goal

Apply the v1.1.0 portfolio treatment to NPI Provider Contact Finder:
- Emoji labels on all input schema fields
- Batch search list (`searchQueriesList`) for all search modes, deduped by NPI number
- README rewrite targeting converting markets
- Version bump to 2.1.0

---

## Context

The actor already has:
- `npiNumbers` (JSON array) + `npiFile` (CSV upload) for `bulk_lookup` mode
- Free tier enforcement + messaging in logs and final status
- Version `2.0.0`

What's missing: emoji labels, a batch search list for search modes, and a conversion-optimized README.

---

## Section 1: Input Schema Changes

File: `.actor/input_schema.json`

### 1a. Emoji labels

Add emoji prefixes to all `title` and `sectionCaption` fields:

| Field | Current title/sectionCaption | New |
|---|---|---|
| `mode` sectionCaption | `Scraping Mode` | `🔍 Scraping Mode` |
| `mode` title | `Scraping mode` | `🔍 Scraping mode` |
| `query` sectionCaption | `Search Filters` | `🔎 Search Filters` |
| `query` title | `Search query` | `🔎 Search query` |
| `npiNumber` title | `NPI Number` | `🪪 NPI Number` |
| `npiNumbers` title | `NPI Numbers (bulk)` | `📋 NPI Numbers (bulk)` |
| `npiFile` title | `NPI CSV File URL (bulk)` | `📁 NPI CSV File URL (bulk)` |
| `firstName` title | `First Name` | `👤 First Name` |
| `lastName` title | `Last Name` | `👤 Last Name` |
| `organizationName` title | `Organization Name` | `🏥 Organization Name` |
| `taxonomyDescription` title | `Specialty / Taxonomy` | `🩺 Specialty / Taxonomy` |
| `city` sectionCaption | `Location Filters` | `📍 Location Filters` |
| `city` title | `City` | `🏙️ City` |
| `state` title | `State` | `🗺️ State` |
| `postalCode` title | `Postal Code` | `📮 Postal Code` |
| `countryCode` title | `Country Code` | `🌎 Country Code` |
| `enumerationType` title | `Provider Type` | `🏷️ Provider Type` |
| `maxResults` sectionCaption | `Output Settings` | `📊 Output Settings` |
| `maxResults` title | `Max results` | `📊 Max results` |
| `requestIntervalSecs` sectionCaption | `Advanced Settings` | `⚙️ Advanced Settings` |
| `requestIntervalSecs` title | `Request interval (seconds)` | `⏱️ Request interval (seconds)` |
| `timeoutSecs` title | `HTTP timeout (seconds)` | `⏳ HTTP timeout (seconds)` |
| `maxRetries` title | `Max retries` | `🔁 Max retries` |
| `enableEmailEnrichment` sectionCaption | `Contact Enrichment` | `📧 Contact Enrichment` |
| `enableEmailEnrichment` title | `Enable Email Enrichment` | `📧 Enable Email Enrichment` |
| `enableLinkedInEnrichment` title | `Enable LinkedIn Enrichment` | `💼 Enable LinkedIn Enrichment` |
| `enableSocialMediaEnrichment` title | `Enable Social Media Enrichment` | `📱 Enable Social Media Enrichment` |
| `emailEnrichmentTimeout` title | `Email Enrichment Timeout (seconds)` | `⏱️ Email Enrichment Timeout (seconds)` |

### 1b. New `searchQueriesList` field

Insert after the `query` field, inside the `Search Filters` section:

```json
"searchQueriesList": {
    "title": "🔎 Batch Search Queries",
    "type": "array",
    "description": "Run multiple searches in one go. Each item replaces the 'query' field for one search run. Results are automatically deduped by NPI number across all queries. Works with all search modes. If provided, takes precedence over the single 'query' field.",
    "editor": "stringList",
    "items": { "type": "string" },
    "prefill": ["Cardiology", "Oncology"]
}
```

### 1c. Update `query` description

Append to the existing description: `"For multiple searches in one run, use 'searchQueriesList' instead."`

---

## Section 2: Code Changes

### 2a. `src/models.py`

**Add field to `ScraperInput`:**
```python
queries_list: list[str] = Field(default_factory=list)
```

**Add to `from_actor_input`:**
```python
queries_list=[q.strip() for q in raw.get("searchQueriesList", []) if str(q).strip()],
```

**Update `validate_for_mode`** — for search modes, accept either `query` OR `queries_list`:
- `SEARCH_PROVIDERS`: valid if `query`, `queries_list`, `first_name`, `last_name`, or `npi_number` is provided
- `SEARCH_ORGANIZATIONS`: valid if `organization_name`, `query`, or `queries_list`
- `SEARCH_BY_SPECIALTY`: valid if `taxonomy_description`, `query`, or `queries_list`

### 2b. `src/main.py`

**`searchQueriesList` applies only to search modes** (`search_providers`, `search_organizations`, `search_by_specialty`). For `bulk_lookup` and `get_provider` modes, `queries_list` is ignored and the existing single-run logic is unchanged.

Replace the single-query scrape block with a multi-query loop for search modes. `ScraperInput` has no `frozen=True` so `config.query` is mutable. The scraper reads `self.config.query` lazily on each call (confirmed at `scraper.py:204,211,219`), so mutating it between iterations is safe.

```python
SEARCH_MODES = {ScrapingMode.SEARCH_PROVIDERS, ScrapingMode.SEARCH_ORGANIZATIONS, ScrapingMode.SEARCH_BY_SPECIALTY}

# Build effective query list (search modes only)
if config.mode in SEARCH_MODES and config.queries_list:
    search_queries = config.queries_list
else:
    search_queries = [config.query] if config.query else [""]

seen_npis: set[str] = set()

for query in search_queries:
    if count >= max_results:
        break  # max_results applies across all queries combined

    config.query = query
    if len(search_queries) > 1:
        Actor.log.info(f"Searching for query: {query!r}")

    scrape_iter = (
        scraper.scrape_bulk()
        if config.mode == ScrapingMode.BULK_LOOKUP
        else scraper.scrape()
    )

    async for item in scrape_iter:
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
            await Actor.push_data(batch)
            batch = []
            await Actor.set_status_message(f"Scraped {count}/{max_results} providers")

if batch:
    await Actor.push_data(batch)
```

`max_results` is enforced both at the top of the outer loop and inside the inner loop to prevent over-fetching.

**Validation message update** — update the `validate_for_mode` error messages for search modes to mention `searchQueriesList`:
- `SEARCH_PROVIDERS`: `"Provide at least one of: query (last name), searchQueriesList, first name, or last name for search_providers."`
- `SEARCH_ORGANIZATIONS`: `"Provide an organization name, query, or searchQueriesList for search_organizations."`
- `SEARCH_BY_SPECIALTY`: `"Provide a taxonomy/specialty description, query, or searchQueriesList for search_by_specialty."`

**`ProviderRecord.schema_version`** — leave at `"2.0"`. This field represents the output schema version, which has not changed. Out of scope.

### 2c. No changes to

- `scraper.py`
- `enrichment.py`
- `utils.py`

---

## Section 3: README Rewrite

**Target audiences (priority order):**
1. Pharma/medical device sales reps — territory prospecting by specialty
2. Healthcare marketing agencies — building contact lists at scale
3. Revenue operations teams — enriching CRM with verified provider emails

**Structure:**

1. One-line hook
2. Value prop (3 bullets max)
3. Quick start — specialty batch example (leads with new feature)
4. Input reference table
5. Batch Search section (new)
6. Bulk Upload section (existing, moved lower)
7. FAQ

**Tone:** Direct, outcome-focused. "Build a territory list in one run" not "supports 5 scraping modes."

---

## Section 4: Version + Release

- Bump `version` in `.actor/actor.json`: `"2.0.0"` → `"2.1.0"`
- Commit message: `feat: v2.1.0 — batch search, emoji labels, README rewrite`
- No changes to `.gitignore` needed (`.arc/` already excluded or not present)

---

## Out of Scope

- No changes to scraping logic, enrichment, or API calls
- No new scraping modes
- LinkedIn enrichment placeholder left as-is
