# NPI Provider Contact Finder v2.1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add emoji labels, `searchQueriesList` batch input, README rewrite, and version bump to 2.1.0.

**Architecture:** Input schema gets emoji labels and a new `searchQueriesList` field. `ScraperInput` model gains a `queries_list` field. `main.py` wraps the existing `scraper.scrape()` path in a multi-query outer loop with NPI-based deduplication. `scrape_bulk()` path is unchanged. No changes to scraper, enrichment, or utils.

**Tech Stack:** Python, Pydantic v2, Apify SDK, JSON input schema

**Spec:** `docs/superpowers/specs/2026-03-20-npi-contact-finder-v2.1.0-design.md`

---

## File Map

| File | Change |
|---|---|
| `.actor/input_schema.json` | Emoji labels on all titles/sectionCaptions, add `searchQueriesList`, remove `additionalProperties: false`, update `query` description |
| `.actor/actor.json` | Version bump `2.0.0` → `2.1.0` |
| `src/models.py` | Add `queries_list` field, update `from_actor_input`, update `validate_for_mode` guards |
| `src/main.py` | Add `SEARCH_MODES` set, wrap search path in multi-query loop with NPI dedup |
| `README.md` | Full rewrite — two featured workflows, input table, FAQ |

---

## Task 1: Input Schema — Emoji Labels

**Files:**
- Modify: `.actor/input_schema.json`

- [ ] **Step 1: Add emoji prefixes to all `sectionCaption` fields**

  Edit `.actor/input_schema.json` — update these `sectionCaption` values:
  - `"Scraping Mode"` → `"🔍 Scraping Mode"`
  - `"Search Filters"` → `"🔎 Search Filters"`
  - `"Location Filters"` → `"📍 Location Filters"`
  - `"Output Settings"` → `"📊 Output Settings"`
  - `"Advanced Settings"` → `"⚙️ Advanced Settings"`
  - `"Contact Enrichment"` → `"📧 Contact Enrichment"`

- [ ] **Step 2: Add emoji prefixes to all `title` fields**

  Edit `.actor/input_schema.json` — update these `title` values:
  - `mode`: `"🔍 Scraping mode"`
  - `query`: `"🔎 Search query"`
  - `npiNumber`: `"🪪 NPI Number"`
  - `npiNumbers`: `"📋 NPI Numbers (bulk)"`
  - `npiFile`: `"📁 NPI CSV File URL (bulk)"`
  - `firstName`: `"👤 First Name"`
  - `lastName`: `"👤 Last Name"`
  - `organizationName`: `"🏥 Organization Name"`
  - `taxonomyDescription`: `"🩺 Specialty / Taxonomy"`
  - `city`: `"🏙️ City"`
  - `state`: `"🗺️ State"`
  - `postalCode`: `"📮 Postal Code"`
  - `countryCode`: `"🌎 Country Code"`
  - `enumerationType`: `"🏷️ Provider Type"`
  - `maxResults`: `"📊 Max results"`
  - `requestIntervalSecs`: `"⏱️ Request interval (seconds)"`
  - `timeoutSecs`: `"⏳ HTTP timeout (seconds)"`
  - `maxRetries`: `"🔁 Max retries"`
  - `enableEmailEnrichment`: `"📧 Enable Email Enrichment"`
  - `enableLinkedInEnrichment`: `"💼 Enable LinkedIn Enrichment"`
  - `enableSocialMediaEnrichment`: `"📱 Enable Social Media Enrichment"`
  - `emailEnrichmentTimeout`: `"⏱️ Email Enrichment Timeout (seconds)"`

- [ ] **Step 3: Commit**

  ```bash
  git add .actor/input_schema.json
  git commit -m "feat: emoji labels on all input schema fields"
  ```

---

## Task 2: Input Schema — Add `searchQueriesList` + Housekeeping

**Files:**
- Modify: `.actor/input_schema.json`

- [ ] **Step 1: Insert `searchQueriesList` after the `query` field**

  Add this block to `properties` immediately after the `query` field. Do NOT add a `sectionCaption` — it inherits the Search Filters section from `query`:

  ```json
  "searchQueriesList": {
      "title": "🔎 Batch Search Queries",
      "type": "array",
      "description": "Run multiple searches in one go. Each item replaces the 'query' field for one search run. Results are automatically deduped by NPI number across all queries. Works with search_providers, search_organizations, and search_by_specialty modes. If provided, takes precedence over the single 'query' field.",
      "editor": "stringList",
      "items": { "type": "string" },
      "prefill": ["Cardiology", "Oncology"]
  },
  ```

- [ ] **Step 2: Update `query` description**

  Append to the existing `query` description field:
  `" For multiple searches in one run, use 'searchQueriesList' instead."`

- [ ] **Step 3: Remove `additionalProperties: false`**

  Delete the line `"additionalProperties": false` near the end of the file (line 184). Without removing it, Apify's schema validator rejects any run that passes `searchQueriesList`.

- [ ] **Step 4: Verify the file is valid JSON**

  ```bash
  python3 -c "import json; json.load(open('.actor/input_schema.json')); print('valid')"
  ```
  Expected: `valid`

- [ ] **Step 5: Commit**

  ```bash
  git add .actor/input_schema.json
  git commit -m "feat: add searchQueriesList batch input field"
  ```

---

## Task 3: Models — Add `queries_list` Field

**Files:**
- Modify: `src/models.py`

- [ ] **Step 1: Add `queries_list` field to `ScraperInput`**

  In `src/models.py`, add after the `npi_numbers` field (line 38):

  ```python
  queries_list: list[str] = Field(default_factory=list)
  ```

- [ ] **Step 2: Add to `from_actor_input`**

  In `from_actor_input`, add after the `npi_numbers` line:

  ```python
  queries_list=[q.strip() for q in raw.get("searchQueriesList", []) if str(q).strip()],
  ```

- [ ] **Step 3: Update `validate_for_mode` guards for search modes**

  Replace the three search-mode guard conditions (lines 87–95) with:

  ```python
  if self.mode == ScrapingMode.SEARCH_PROVIDERS:
      if not (self.query or self.queries_list or self.first_name or self.last_name or self.npi_number):
          return "Provide at least one of: query (last name), searchQueriesList, first name, or last name for search_providers."
  if self.mode == ScrapingMode.SEARCH_ORGANIZATIONS:
      if not (self.organization_name or self.query or self.queries_list):
          return "Provide an organization name, query, or searchQueriesList for search_organizations."
  if self.mode == ScrapingMode.SEARCH_BY_SPECIALTY:
      if not (self.taxonomy_description or self.query or self.queries_list):
          return "Provide a taxonomy/specialty description, query, or searchQueriesList for search_by_specialty."
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add src/models.py
  git commit -m "feat: add queries_list to ScraperInput model"
  ```

---

## Task 4: Main — Multi-Query Loop with Dedup

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Add `SEARCH_MODES` constant after imports**

  After the `from .models import ScraperInput, ScrapingMode` import line, add:

  ```python
  SEARCH_MODES = {ScrapingMode.SEARCH_PROVIDERS, ScrapingMode.SEARCH_ORGANIZATIONS, ScrapingMode.SEARCH_BY_SPECIALTY}
  ```

- [ ] **Step 2: Replace the scrape iteration block**

  The current scrape block is **lines 93–120 in their entirety** — this includes the ternary at lines 93–97, the `try:` at line 99, and the `except Exception` at lines 116–120. **Delete all of lines 93–120** and replace with the block below. Do not keep the old `try`/`except` wrapper.

  Note: `get_provider` mode also routes through the `else` branch. This is safe — `scraper.scrape()` reads `config.mode` internally and handles `get_provider` via `config.npi_number`, not `config.query`. The multi-query loop runs once with `search_queries = [config.query]` (or `[""]`), which is equivalent to the original single-run behavior.

  ```python
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
                  await Actor.push_data(batch)
                  batch = []
                  await Actor.set_status_message(f"Scraped {count}/{max_results} providers")
          if batch:
              await Actor.push_data(batch)
      except Exception as e:
          state["failed"] += 1
          Actor.log.error(f"Scraping error: {e}")
          if batch:
              await Actor.push_data(batch)
  else:
      # Multi-query loop for all search modes
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
                      await Actor.push_data(batch)
                      batch = []
                      await Actor.set_status_message(f"Scraped {count}/{max_results} providers")

          if batch:
              await Actor.push_data(batch)

      except Exception as e:
          state["failed"] += 1
          Actor.log.error(f"Scraping error: {e}")
          if batch:
              await Actor.push_data(batch)
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add src/main.py
  git commit -m "feat: multi-query loop with NPI dedup for searchQueriesList"
  ```

---

## Task 5: README Rewrite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Draft README via local model**

  Use `mcp__ratbyte-rag__local_generate_code` or `mcp__ratbyte-rag__local_write_blog` with this prompt:

  > Write a README for an Apify actor called "NPI Provider Contact Finder". Target audiences: pharma/medical device sales reps doing territory prospecting, healthcare marketing agencies, RevOps teams enriching CRMs. Tone: direct, outcome-focused, no fluff.
  >
  > Structure:
  > 1. One-line hook
  > 2. Value prop (3 bullets: cost vs $50K+ databases, real-time NPPES API, email/contact enrichment)
  > 3. Two featured workflows as equal named sections:
  >    - "Batch Search by Specialty or Name" — show searchQueriesList JSON example with ["Cardiology", "Oncology"] in search_by_specialty mode
  >    - "Bulk Enrich by NPI Number" — two paths: (a) small list as JSON array npiNumbers, (b) large list via Apify Key-Value Store CSV upload with full step-by-step: create store → upload CSV → copy API URL (not console URL) → paste into npiFile field → set mode to bulk_lookup
  > 4. Input reference table with columns: Field, Type, Default, Description. All fields grouped by: Search, Location, Output, Advanced, Enrichment.
  > 5. FAQ: free tier limits, what NPI is, how email enrichment works, pricing

- [ ] **Step 2: Claude review pass**

  Review the draft. Ensure:
  - KV Store step-by-step is complete and warns about console URL vs API URL
  - `searchQueriesList` example JSON is correct and shows a realistic pharma rep use case
  - Input table covers all fields including the new `searchQueriesList`
  - No marketing buzzwords, no emojis in body text (emojis only in section headers where appropriate)
  - Free tier limit (25 results) is mentioned in FAQ

- [ ] **Step 3: Commit**

  ```bash
  git add README.md
  git commit -m "docs: rewrite README — batch search + bulk NPI workflows"
  ```

---

## Task 6: Version Bump + Push

**Files:**
- Modify: `.actor/actor.json`

- [ ] **Step 1: Bump version in actor.json**

  Change `"version": "2.0.0"` to `"version": "2.1.0"` in `.actor/actor.json`.

- [ ] **Step 2: Final commit and push**

  ```bash
  git add .actor/actor.json
  git commit -m "feat: v2.1.0 — batch search, emoji labels, README rewrite"
  git push
  ```
