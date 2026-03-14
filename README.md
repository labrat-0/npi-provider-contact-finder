# NPI Provider Contact Finder

> **Generate healthcare sales leads with verified provider contact information. Find doctor emails, practice websites, and social media profiles from the NPPES NPI Registry. Perfect for medical device sales, pharma outreach, and healthcare marketing. No API key required.**

Transform raw NPI provider data into actionable sales leads. Get email addresses, LinkedIn profiles, and contact information for 6+ million US healthcare providers. Replace expensive healthcare databases (IQVIA, Definitive Healthcare) that cost $50K+/year with pay-per-contact pricing.

---

## What does it do?

**NPI Provider Contact Finder** enhances basic NPI provider lookups with contact enrichment. Search the NPPES registry for providers, then automatically scrape practice websites for emails, office manager contacts, and social media profiles.

### **Business Value**

💰 **Cost Savings**: Replace $50K+/year healthcare databases with $0.70-$1.00 per 1,000 contacts
📧 **Email Enrichment**: Find practice emails, office manager contacts, billing emails
🎯 **Outreach-Ready Leads**: Get verified contacts for cold outreach, not just public NPI data
📱 **Social Discovery**: LinkedIn, Facebook, Healthgrades, Vitals profiles
🚀 **Scale Instantly**: Generate 10K+ healthcare leads in minutes, not months

### **🔥 Technical Advantage**

⚡ **Real-Time CMS API**: Direct integration with official NPPES API (daily updates) vs competitors using month-old 4GB+ file dumps
🛠️ **Zero Setup**: No database imports, no technical expertise required vs competitors requiring "requisite technical expertise"
📞 **Professional Support**: Full documentation and support vs CMS official "no help desk available" for file-based solutions
✅ **Enterprise Ready**: FOIA-compliant data foundation with bulletproof legal basis

---

## Use Cases

### 🩺 **Medical Device Sales Teams**

**Problem**: Building targeted lists of cardiologists in California takes weeks of manual research.

**Solution**: Search for "Cardiology" providers in CA → Get 1,000+ contacts with practice emails and LinkedIn profiles in 10 minutes.

**ROI**: Sales rep time saved = $5K/month. Device sales cycle shortened by 30 days.

**Example**:
```json
{
    "mode": "search_by_specialty",
    "taxonomyDescription": "Cardiology",
    "state": "CA",
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true,
    "maxResults": 1000
}
```

---

### 💊 **Pharmaceutical Sales & Marketing**

**Problem**: Pharma reps need oncologist contacts for new drug launch. IQVIA costs $30K/year.

**Solution**: Search oncologists by state → Enrich with emails and social profiles → Export to CRM.

**ROI**: $30K/year subscription replaced with $7 one-time cost (10K contacts @ $0.70/1K).

**Example**:
```json
{
    "mode": "search_by_specialty",
    "taxonomyDescription": "Oncology",
    "state": "TX",
    "city": "Houston",
    "enableEmailEnrichment": true,
    "maxResults": 500
}
```

---

### 🏥 **Healthcare IT & SaaS Vendors**

**Problem**: EHR vendor needs to reach primary care practices for demo outreach.

**Solution**: Search "Family Medicine" providers → Filter by state → Get office manager emails for decision-maker outreach.

**ROI**: 5% conversion on 10K leads = 500 demos scheduled. Cost: $7 vs months of manual research.

**Example**:
```json
{
    "mode": "search_by_specialty",
    "taxonomyDescription": "Family Medicine",
    "state": "FL",
    "enableEmailEnrichment": true,
    "maxResults": 10000
}
```

---

### 📊 **Market Research & Competitive Intelligence**

**Problem**: Biotech needs to map competitor drug trial investigators across US.

**Solution**: Search providers by specialty + city → Cross-reference with ClinicalTrials.gov data.

**ROI**: Competitive intelligence report delivered in 2 hours vs 2 weeks.

---

### 🤖 **AI Agents & Automation**

**Problem**: Healthcare AI assistant needs real-time provider lookup with contact info.

**Solution**: Use as MCP tool → Agent can search providers and enrich contacts on-demand.

**Example**: "Find 10 dermatologists in Seattle with email addresses" → Agent calls actor → Returns enriched results.

---

## Input

Choose a search mode and enable contact enrichment options.

### Mode 1: Search Providers (with Email Enrichment)

Search for individual providers and enrich with contact information.

```json
{
    "mode": "search_providers",
    "lastName": "Smith",
    "state": "NY",
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true,
    "maxResults": 100
}
```

### Mode 2: Search by Specialty (Lead Generation)

Find all providers in a specialty, perfect for building sales lists.

```json
{
    "mode": "search_by_specialty",
    "taxonomyDescription": "Internal Medicine",
    "state": "CA",
    "city": "Los Angeles",
    "enableEmailEnrichment": true,
    "enableSocialMediaEnrichment": true,
    "maxResults": 1000
}
```

### Mode 3: Get Specific Provider (Deep Enrichment)

Look up a single provider by NPI with full contact enrichment.

```json
{
    "mode": "get_provider",
    "npiNumber": "1871538041",
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true,
    "enableSocialMediaEnrichment": true
}
```

### Mode 4: Search Organizations (Hospital/Clinic Contacts)

Find hospitals, clinics, group practices with decision-maker contacts.

```json
{
    "mode": "search_organizations",
    "organizationName": "Mayo Clinic",
    "enableEmailEnrichment": true,
    "maxResults": 50
}
```

### Mode 5: Bulk Lookup (CSV or JSON list)

Look up a list of NPI numbers in bulk — perfect for enriching an existing CRM export or processing a vendor-supplied provider list.

**Option A — JSON array:**
```json
{
    "mode": "bulk_lookup",
    "npiNumbers": ["1871538041", "1932102168", "1245319599"],
    "enableEmailEnrichment": true,
    "enableLinkedInEnrichment": true
}
```

**Option B — CSV file upload:**
```json
{
    "mode": "bulk_lookup",
    "npiFile": "https://your-storage/npis.csv",
    "enableEmailEnrichment": true
}
```

The CSV file should have a column named `npi`, `npi_number`, or `NPI` — or just one NPI number per row. All enrichment flags work the same as single-provider modes.

---

## Contact Enrichment Options

| Option | Description | Use Case | Pricing Impact |
|--------|-------------|----------|----------------|
| `enableEmailEnrichment` | Scrape practice website for emails | Get office manager, billing contacts | +$0.30/1K contacts |
| `enableLinkedInEnrichment` | Find provider LinkedIn profiles | B2B outreach, relationship building | +$0.50/1K contacts |
| `enableSocialMediaEnrichment` | Extract all social media links | Multi-channel marketing | +$0.20/1K contacts |

**Recommended**: Enable `emailEnrichment` for all lead generation use cases.

---

## Output

### Base Provider Data (from NPPES)

All the standard NPI fields from NPPES:

| Field | Description |
|-------|-------------|
| `npi_number` | 10-digit National Provider Identifier |
| `first_name`, `last_name` | Provider name |
| `credential` | MD, DO, NP, PA, PharmD, etc. |
| `primary_specialty` | Primary taxonomy/specialty |
| `addresses` | Practice and mailing addresses |
| `telephone_number` | Practice phone |
| `taxonomies` | All specialties with licenses |
| `status` | Active (A) or Deactivated (D) |

### Enriched Contact Data (NEW)

When enrichment is enabled, each provider includes:

```json
{
    "contact_enrichment": {
        "emails": ["office@practice.com", "billing@practice.com"],
        "primary_email": "office@practice.com",
        "office_email": "office@practice.com",
        "billing_email": "billing@practice.com",
        "practice_website": "https://drsmithcardiology.com",
        "linkedin_profile_url": "https://linkedin.com/in/johnsmith-md",
        "facebook_url": "https://facebook.com/drsmithcardiology",
        "healthgrades_url": "https://healthgrades.com/physician/dr-smith",
        "office_manager_email": "manager@practice.com",
        "enrichment_timestamp": "2026-03-07T18:30:00Z",
        "enrichment_sources": ["https://drsmithcardiology.com"]
    }
}
```

### Example: Enriched Provider (Cardiologist in Texas)

```json
{
    "schema_version": "2.0",
    "type": "provider_with_contacts",
    "npi_number": "1871538041",
    "enumeration_type": "NPI-1",
    "first_name": "JACK",
    "last_name": "SMITH",
    "credential": "MD",
    "sex": "M",
    "primary_specialty": "Cardiology",
    "practice_address_city": "HOUSTON",
    "practice_address_state": "TX",
    "addresses": [
        {
            "address_purpose": "LOCATION",
            "address_1": "1234 MEDICAL CENTER BLVD",
            "city": "HOUSTON",
            "state": "TX",
            "postal_code": "77030",
            "telephone_number": "713-555-0100"
        }
    ],
    "taxonomies": [
        {
            "code": "207RC0000X",
            "description": "Cardiology",
            "license": "L12345",
            "state": "TX",
            "primary": true
        }
    ],
    "contact_enrichment": {
        "emails": [
            "office@houstonheartdocs.com",
            "billing@houstonheartdocs.com",
            "appointments@houstonheartdocs.com"
        ],
        "primary_email": "office@houstonheartdocs.com",
        "office_email": "office@houstonheartdocs.com",
        "billing_email": "billing@houstonheartdocs.com",
        "practice_website": "https://houstonheartdocs.com",
        "website_scraped": true,
        "linkedin_profile_url": "https://linkedin.com/in/jacksmith-md-cardiology",
        "facebook_url": "https://facebook.com/houstonheartdoctors",
        "healthgrades_url": "https://healthgrades.com/physician/dr-jack-smith",
        "enrichment_timestamp": "2026-03-07T18:30:00Z",
        "enrichment_sources": ["https://houstonheartdocs.com"]
    },
    "npi_registry_url": "https://npiregistry.cms.hhs.gov/provider-view/1871538041"
}
```

---

## Pricing

### Pay-Per-Contact Pricing (Not Pay-Per-Result)

We charge based on how many providers you scrape, **with add-on pricing for enrichment**.

| Tier | Base Provider Data | + Email Enrichment | + LinkedIn Enrichment | + Full Enrichment |
|------|-------------------|-------------------|----------------------|-------------------|
| **Standard** | $0.70 / 1,000 contacts | +$0.30 / 1,000 | +$0.50 / 1,000 | +$0.80 / 1,000 |
| **Example: 1K contacts** | $0.70 | $1.00 | $1.20 | $1.50 |
| **Example: 10K contacts** | $7.00 | $10.00 | $12.00 | $15.00 |
| **Example: 100K contacts** | $70.00 | $100.00 | $120.00 | $150.00 |

### Pricing Calculator

**Your Use Case**: Generate 5,000 cardiology leads in California with emails

**Cost Breakdown**:
- Base NPI data: 5,000 contacts × $0.70/1K = **$3.50**
- Email enrichment: 5,000 contacts × $0.30/1K = **$1.50**
- **Total**: **$5.00**

**Compare to Alternatives**:
- IQVIA Physician Universe: **$50,000/year** (minimum)
- Definitive Healthcare: **$35,000/year**
- ZoomInfo Healthcare: **$25,000/year**
- Manual research (sales rep @ $75/hr): **$3,750** (50 hours for 5K contacts)

**Savings**: 99.99% vs IQVIA, 99.98% vs Definitive, 99.87% vs manual research

---

## Common Specialties (Taxonomy Codes)

| Specialty | Taxonomy Code | Avg Providers in US |
|-----------|---------------|---------------------|
| Internal Medicine | 207R00000X | 180,000+ |
| Family Medicine | 207Q00000X | 140,000+ |
| Cardiology | 207RC0000X | 25,000+ |
| Oncology | 207RX0202X | 12,000+ |
| Orthopedic Surgery | 207X00000X | 28,000+ |
| Psychiatry | 2084P0800X | 45,000+ |
| Pediatrics | 208000000X | 90,000+ |
| Dermatology | 207N00000X | 13,000+ |
| Neurology | 2084N0400X | 17,000+ |
| Emergency Medicine | 207P00000X | 48,000+ |

**Pro Tip**: Combine specialty with state/city filters for highly targeted lists.

---

## Integrations

### Apify API

```bash
curl "https://api.apify.com/v2/acts/labrat011~npi-provider-contact-finder/runs" \
  -X POST \
  -H "Authorization: Bearer <APIFY_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "search_by_specialty",
    "taxonomyDescription": "Cardiology",
    "state": "CA",
    "enableEmailEnrichment": true,
    "maxResults": 1000
  }'
```

### Python (Generate Leads Programmatically)

```python
from apify_client import ApifyClient

client = ApifyClient("<APIFY_TOKEN>")

# Generate 1,000 oncology leads in New York with emails
run = client.actor("labrat011/npi-provider-contact-finder").call(run_input={
    "mode": "search_by_specialty",
    "taxonomyDescription": "Oncology",
    "state": "NY",
    "enableEmailEnrichment": True,
    "maxResults": 1000
})

# Export to CRM
for provider in client.dataset(run["defaultDatasetId"]).iterate_items():
    if provider.get('contact_enrichment'):
        enrichment = provider['contact_enrichment']
        print(f"Lead: {provider['first_name']} {provider['last_name']}")
        print(f"Email: {enrichment.get('primary_email')}")
        print(f"Specialty: {provider['primary_specialty']}")
        print(f"City: {provider['practice_address_city']}, {provider['practice_address_state']}")
        print("---")
```

### JavaScript/Node.js

```javascript
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({ token: '<APIFY_TOKEN>' });

const run = await client.actor('labrat011/npi-provider-contact-finder').call({
    mode: 'search_by_specialty',
    taxonomyDescription: 'Dermatology',
    state: 'FL',
    enableEmailEnrichment: true,
    enableLinkedInEnrichment: true,
    maxResults: 500
});

const { items } = await client.dataset(run.defaultDatasetId).listItems();

// Filter providers with email addresses
const contactableLeads = items.filter(p => 
    p.contact_enrichment?.primary_email
);

console.log(`Found ${contactableLeads.length} contactable dermatology leads in FL`);
```

---

## MCP Integration (AI Agents)

This actor works as an MCP tool for AI agents. No custom server needed.

- **Endpoint:** `https://mcp.apify.com?tools=labrat011/npi-provider-contact-finder`
- **Auth:** `Authorization: Bearer <APIFY_TOKEN>`
- **Works with:** Claude Desktop, Cursor, VS Code, Windsurf, ChatGPT

**Example MCP config (Claude Desktop):**

```json
{
    "mcpServers": {
        "npi-contact-finder": {
            "url": "https://mcp.apify.com?tools=labrat011/npi-provider-contact-finder",
            "headers": {
                "Authorization": "Bearer <APIFY_TOKEN>"
            }
        }
    }
}
```

**AI Agent Use Case**:

User: "Find me 50 cardiologists in Boston with email addresses"

Agent: 
1. Calls `npi-provider-contact-finder` actor
2. Searches for Cardiology providers in Boston, MA
3. Enables email enrichment
4. Returns formatted list of 50 contactable cardiologists

---

## FAQ

### What makes this different from the basic NPI Scraper?

**Basic NPI Scraper**: Returns only public NPI data (name, address, specialty, phone)

**NPI Provider Contact Finder**: Adds email enrichment, LinkedIn profiles, social media links, and office manager contacts by scraping practice websites.

**Use the basic NPI scraper if**: You just need to verify provider credentials or build a directory.

**Use the Contact Finder if**: You need to actually reach out to providers (sales, marketing, partnerships).

---

### How accurate are the enriched emails?

Email enrichment scrapes the practice's official website listed in public directories. Accuracy depends on:

- **Website availability**: ~80% of providers have findable practice websites
- **Email visibility**: ~60% of practice websites display email addresses
- **Overall enrichment rate**: ~45-50% of providers will have at least one email found

**Pro Tip**: For highest enrichment rates, target group practices and specialists (they're more likely to have robust websites).

---

### Is it legal to scrape provider emails from websites?

Yes. We scrape publicly available information from practice websites. This is similar to how sales tools like ZoomInfo and Clearbit work.

**Key Points**:
- We only scrape public websites (not password-protected portals)
- NPI data itself is public domain (from CMS)
- Email addresses displayed on public websites are intended for contact
- You're responsible for complying with CAN-SPAM, GDPR, and other marketing regulations when using the data

**Not Legal Advice**: Consult your legal team for compliance with your specific use case.

---

### Can I use this for cold email outreach?

Yes, but you must comply with regulations:

**CAN-SPAM Act (US)**:
- Include physical mailing address in emails
- Provide clear unsubscribe mechanism
- Honor opt-out requests within 10 days
- Don't use deceptive subject lines

**GDPR (EU)**:
- Only contact EU providers if you have legitimate interest or consent
- Provide privacy policy and data usage disclosure
- Honor data deletion requests

**Best Practice**: Use emails for initial outreach, then ask for consent for ongoing communications.

---

### What's the enrichment timeout setting?

`emailEnrichmentTimeout` controls how long we wait when scraping each practice website (default: 10 seconds).

**Recommendations**:
- **Fast mode**: 5 seconds (may miss some emails, but faster runs)
- **Standard**: 10 seconds (balanced)
- **Thorough**: 20 seconds (slower, but highest enrichment rate)

---

### How current is the NPI data?

The NPPES database is updated weekly by CMS. We query the live API on each run, so data is always current.

**Provider updates we capture**:
- New provider enrollments
- Address changes
- Status changes (active → deactivated)
- Specialty additions/changes

---

### Can I filter by multiple specialties?

Use multiple runs with `search_by_specialty` mode, one for each specialty. Then merge results.

**Example**: To get both Cardiology AND Oncology providers in Texas:
1. Run 1: `taxonomyDescription: "Cardiology"`, `state: "TX"`
2. Run 2: `taxonomyDescription: "Oncology"`, `state: "TX"`
3. Merge datasets

**Alternative**: Use the [Apify Orchestrator](/lukaskrivka/google-maps-scraper-orchestrator) pattern to run multiple searches in parallel and merge results.

---

### Does this work for international providers?

No, NPPES is US-only. NPI numbers are only issued to US healthcare providers and organizations.

**US Territories Included**: Puerto Rico, US Virgin Islands, Guam

**For International**: You'd need country-specific provider registries (UK GMC, Canada CPSO, etc.).

---

### Can I integrate this with my CRM?

Yes! Use these integration options:

**Salesforce**: Use Zapier or Make to push enriched providers as leads
**HubSpot**: Connect via Apify webhooks to create contacts
**Pipedrive**: Use Apify API to push deals with provider contact info
**Custom CRM**: Use Apify API to fetch results as JSON/CSV, then import

**Example Zapier Workflow**:
1. Trigger: Apify run finishes
2. Action: Get dataset items
3. Action: Create Salesforce leads with provider email

---

### How can I speed up enrichment?

**Tips for faster runs**:
1. **Reduce timeout**: Set `emailEnrichmentTimeout: 5` for faster website scraping
2. **Disable LinkedIn enrichment**: LinkedIn search is slower than email scraping
3. **Run multiple actors in parallel**: Use Orchestrator to split searches across states
4. **Increase memory**: Higher memory = more parallel website scraping

**Speed benchmarks** (with email enrichment):
- 100 providers: ~2 minutes
- 1,000 providers: ~15 minutes
- 10,000 providers: ~2 hours

---

### What if a provider has no website?

The enrichment will return empty for that provider. You'll still get the base NPI data (name, address, phone, specialty).

**Enrichment success rates by provider type**:
- Group practices: ~70% (usually have robust websites)
- Solo practitioners: ~40% (many don't have websites)
- Specialists: ~60% (more likely to have online presence)
- Primary care: ~45% (mixed)

---

## You might also like

**Related Healthcare Lead Gen Tools**:

- 🏥 **Medicare Provider Directory + Contacts** - C-suite contacts at 6,000+ hospitals
- 💊 **Clinical Trial Site Contacts** - Principal investigators conducting trials
- 🏪 **Pharmacy Chain Locations + Contacts** - 70K+ pharmacies with buyer emails
- ⚠️ **FDA Adverse Events Scraper** - Drug safety intelligence for pharma competitive analysis

**Other Lead Gen Patterns**:

- 📍 **Google Maps Scraper** (compass) - Local business lead generation
- 📧 **Email Enrichment Tools** - Validate and enhance email lists

---

## Resources

- [NPPES NPI Registry](https://npiregistry.cms.hhs.gov/)
- [NPI Registry API Documentation](https://npiregistry.cms.hhs.gov/api-page)
- [Healthcare Provider Taxonomy Codes](https://taxonomy.nucc.org/)
- [CMS NPI FAQ](https://www.cms.gov/Regulations-and-Guidance/Administrative-Simplification/NationalProvIdentStand)
- [CAN-SPAM Compliance Guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
- [Apify Documentation](https://docs.apify.com/)

---

## Legal Disclaimer

This actor scrapes publicly available data from the NPPES NPI Registry (public domain) and publicly accessible practice websites. Users are responsible for:

- Complying with CAN-SPAM, GDPR, and other marketing regulations
- Obtaining necessary consents for email communications
- Respecting website robots.txt and terms of service
- Using data ethically and in accordance with applicable laws

NPI data is provided by CMS and is in the public domain. Practice website data is publicly available information intended for contact purposes.

---

## License

This actor is provided under the MIT License. NPI data is from CMS and is in the public domain.

---

**Questions? Issues?** → [Open an issue on GitHub](https://github.com/labrat-0/npi-provider-contact-finder/issues)

**Need custom healthcare data scraping?** → [Contact us](/contact)
