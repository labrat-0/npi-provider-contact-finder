"""Contact enrichment module for NPI Provider Contact Finder.

Scrapes practice websites for email addresses, social media profiles,
and additional contact information.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse, urlencode

import httpx
from bs4 import BeautifulSoup

from .models import ContactEnrichment
from .utils import RateLimiter

logger = logging.getLogger(__name__)

# Email regex pattern
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Social media URL patterns
SOCIAL_PATTERNS = {
    'linkedin': re.compile(r'https?://(?:www\.)?linkedin\.com/(?:in|company)/[\w-]+/?'),
    'facebook': re.compile(r'https?://(?:www\.)?facebook\.com/[\w.-]+/?'),
    'twitter': re.compile(r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+/?'),
    'instagram': re.compile(r'https?://(?:www\.)?instagram\.com/[\w.]+/?'),
    'healthgrades': re.compile(r'https?://(?:www\.)?healthgrades\.com/physician/[\w-]+'),
    'vitals': re.compile(r'https?://(?:www\.)?vitals\.com/doctors/[\w-]+'),
    'zocdoc': re.compile(r'https?://(?:www\.)?zocdoc\.com/doctor/[\w-]+'),
}


def _extract_emails_from_text(text: str) -> list[str]:
    """Extract unique email addresses from text."""
    matches = EMAIL_PATTERN.findall(text)
    # Filter out common false positives
    emails = []
    for email in matches:
        lower_email = email.lower()
        # Skip image extensions and common false positives
        if not any(lower_email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
            if '@' in email and '.' in email.split('@')[1]:
                emails.append(email)
    return list(set(emails))


def _extract_social_urls(html: str, base_url: str) -> dict[str, str]:
    """Extract social media URLs from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    social_urls = {}
    
    # Find all links
    for link in soup.find_all('a', href=True):
        href = link['href']
        absolute_url = urljoin(base_url, href)
        
        for platform, pattern in SOCIAL_PATTERNS.items():
            if pattern.search(absolute_url):
                if platform not in social_urls:  # Only take first match
                    social_urls[platform] = absolute_url
    
    return social_urls


def _classify_emails(emails: list[str]) -> dict[str, str]:
    """Classify emails by type (office, billing, general)."""
    classified = {
        'primary': '',
        'office': '',
        'billing': '',
    }
    
    if not emails:
        return classified
    
    # Look for specific email types
    for email in emails:
        lower = email.lower()
        if 'billing' in lower or 'accounts' in lower:
            if not classified['billing']:
                classified['billing'] = email
        elif 'office' in lower or 'admin' in lower or 'manager' in lower:
            if not classified['office']:
                classified['office'] = email
        elif 'info' in lower or 'contact' in lower or 'hello' in lower:
            if not classified['primary']:
                classified['primary'] = email
    
    # If no classified email, use first one as primary
    if not classified['primary'] and emails:
        classified['primary'] = emails[0]
    
    return classified


# Domains to skip when evaluating DuckDuckGo search results
# These are directories / aggregators, not practice websites
_DIRECTORY_DOMAINS = frozenset([
    'healthgrades.com', 'vitals.com', 'zocdoc.com', 'doximity.com',
    'webmd.com', 'ratemds.com', 'yelp.com', 'yellowpages.com',
    'betterdoctor.com', 'castlighthealth.com', 'usnews.com',
    'npiprofile.com', 'npino.com', 'medicare.gov', 'cms.gov',
    'facebook.com', 'twitter.com', 'x.com', 'linkedin.com',
    'instagram.com', 'bing.com', 'google.com', 'duckduckgo.com',
    'wikipedia.org', 'wikimedia.org',
])


async def _discover_practice_website(
    provider_name: str,
    city: str,
    state: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
) -> str:
    """
    Discover a practice website URL using DuckDuckGo HTML search.

    Args:
        provider_name: Provider full name (individual) or organization name
        city: Practice city
        state: Practice state abbreviation (e.g. "NY")
        client: HTTP client
        rate_limiter: Rate limiter
        timeout: Request timeout in seconds

    Returns:
        Practice website URL if found, empty string otherwise
    """
    if not provider_name:
        return ""

    # Build a specific search query
    query_parts = [provider_name]
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query_parts.append("medical practice")
    query = " ".join(query_parts)

    search_url = "https://html.duckduckgo.com/html/?" + urlencode({"q": query})

    try:
        await rate_limiter.wait()

        response = await client.get(
            search_url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if response.status_code != 200:
            logger.warning(
                f"DuckDuckGo search returned HTTP {response.status_code} for query: {query}"
            )
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        # DuckDuckGo HTML results use <a class="result__url"> or <a class="result__a">
        # We iterate result links and skip known directory domains
        for result in soup.select("a.result__a"):
            href = result.get("href", "")
            if not href or href.startswith("#"):
                continue

            # DuckDuckGo wraps redirect URLs; extract the real URL from uddg param
            if "duckduckgo.com" in href and "uddg=" in href:
                from urllib.parse import parse_qs
                parsed = urlparse(href)
                uddg = parse_qs(parsed.query).get("uddg", [""])
                href = uddg[0] if uddg[0] else href

            try:
                parsed_href = urlparse(href)
                domain = parsed_href.netloc.lower().lstrip("www.")
            except Exception:
                continue

            if not domain:
                continue

            # Skip directory/aggregator sites
            if any(domain == d or domain.endswith("." + d) for d in _DIRECTORY_DOMAINS):
                continue

            # Must be http/https
            if parsed_href.scheme not in ("http", "https"):
                continue

            logger.info(f"Website discovery found: {href} for provider {provider_name}")
            return href

        logger.info(f"Website discovery: no result found for {provider_name} in {city}, {state}")
        return ""

    except httpx.TimeoutException:
        logger.warning(f"Timeout during website discovery for {provider_name}")
        return ""
    except httpx.HTTPError as e:
        logger.warning(f"HTTP error during website discovery for {provider_name}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error during website discovery for {provider_name}: {e}")
        return ""


async def enrich_provider_contacts(
    provider_data: dict[str, Any],
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
    enable_linkedin: bool = False,
    enable_social: bool = False,
) -> ContactEnrichment:
    """
    Enrich provider with contact information from practice website.
    
    Args:
        provider_data: Provider record from NPPES
        client: HTTP client for requests
        rate_limiter: Rate limiter for requests
        timeout: Timeout for website scraping (seconds)
        enable_linkedin: Whether to search for LinkedIn profiles
        enable_social: Whether to extract all social media URLs
        
    Returns:
        ContactEnrichment record with discovered contacts
    """
    enrichment = ContactEnrichment(
        enrichment_timestamp=datetime.utcnow().isoformat() + 'Z'
    )

    npi = provider_data.get('npi_number', '')

    # --- Step 1: Check if provider already has a website URL in endpoints ---
    practice_website = ""
    for endpoint in provider_data.get('endpoints', []):
        ep_type = endpoint.get('endpoint_type_description', '').lower()
        ep_value = endpoint.get('endpoint', '')
        if ep_value and ('http' in ep_value or 'www.' in ep_value):
            parsed = urlparse(ep_value if '://' in ep_value else 'https://' + ep_value)
            if parsed.scheme in ('http', 'https'):
                practice_website = ep_value
                logger.info(f"NPI {npi}: using website from endpoints field: {practice_website}")
                break

    # --- Step 2: Discover website via search if not already found ---
    if not practice_website:
        # Build provider name for search query
        first = provider_data.get('first_name', '')
        last = provider_data.get('last_name', '')
        org = provider_data.get('organization_name', '')
        provider_name = (f"{first} {last}".strip()) if (first or last) else org

        # Find practice city/state from LOCATION address
        city = ''
        state = ''
        for addr in provider_data.get('addresses', []):
            if addr.get('address_purpose') == 'LOCATION':
                city = addr.get('city', '')
                state = addr.get('state', '')
                break
        # Fallback to any address
        if not city and provider_data.get('addresses'):
            city = provider_data['addresses'][0].get('city', '')
            state = provider_data['addresses'][0].get('state', '')

        if provider_name:
            practice_website = await _discover_practice_website(
                provider_name=provider_name,
                city=city,
                state=state,
                client=client,
                rate_limiter=rate_limiter,
                timeout=timeout,
            )

    # --- Step 3: Scrape the discovered website ---
    if practice_website:
        enrichment = await enrich_provider_website(
            website_url=practice_website,
            client=client,
            rate_limiter=rate_limiter,
            timeout=timeout,
            enable_social=enable_social,
        )
        # Preserve the enrichment timestamp set above (enrich_provider_website sets its own)
        # Ensure enrichment_sources includes the discovered URL
        if practice_website not in enrichment.enrichment_sources:
            enrichment.enrichment_sources = [practice_website] + enrichment.enrichment_sources

        # Search for LinkedIn profile if requested and not already found
        if enable_linkedin and not enrichment.linkedin_profile_url:
            first = provider_data.get('first_name', '')
            last = provider_data.get('last_name', '')
            org = provider_data.get('organization_name', '')
            provider_name = (f"{first} {last}".strip()) if (first or last) else org
            credential = provider_data.get('credential', '')
            city = ''
            state_val = ''
            for addr in provider_data.get('addresses', []):
                if addr.get('address_purpose') == 'LOCATION':
                    city = addr.get('city', '')
                    state_val = addr.get('state', '')
                    break
            linkedin_url = await search_linkedin_profile(
                provider_name=provider_name,
                city=city,
                state=state_val,
                credential=credential,
                client=client,
            )
            if linkedin_url:
                enrichment.linkedin_profile_url = linkedin_url
    else:
        enrichment.website_scraped = False
        enrichment.website_scrape_error = "No practice website found"
        logger.info(f"Contact enrichment for NPI {npi}: no website discovered")

    return enrichment


async def enrich_provider_website(
    website_url: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
    enable_social: bool = True,
) -> ContactEnrichment:
    """
    Scrape a practice website for contact information.
    
    Args:
        website_url: Practice website URL
        client: HTTP client
        rate_limiter: Rate limiter
        timeout: Request timeout
        enable_social: Whether to extract social media links
        
    Returns:
        ContactEnrichment with discovered contacts
    """
    enrichment = ContactEnrichment(
        practice_website=website_url,
        enrichment_timestamp=datetime.utcnow().isoformat() + 'Z',
    )
    
    try:
        await rate_limiter.wait()
        
        response = await client.get(
            website_url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; NPIContactFinder/1.0)',
                'Accept': 'text/html,application/xhtml+xml',
            }
        )
        
        if response.status_code != 200:
            enrichment.website_scrape_error = f"HTTP {response.status_code}"
            return enrichment
        
        html = response.text
        
        # Extract emails
        emails = _extract_emails_from_text(html)
        enrichment.emails = emails
        
        # Classify emails
        classified = _classify_emails(emails)
        enrichment.primary_email = classified['primary']
        enrichment.office_email = classified['office']
        enrichment.billing_email = classified['billing']
        
        # Extract social media URLs
        if enable_social:
            social_urls = _extract_social_urls(html, website_url)
            enrichment.linkedin_profile_url = social_urls.get('linkedin', '')
            enrichment.facebook_url = social_urls.get('facebook', '')
            enrichment.twitter_url = social_urls.get('twitter', '')
            enrichment.instagram_url = social_urls.get('instagram', '')
            enrichment.healthgrades_url = social_urls.get('healthgrades', '')
            enrichment.vitals_url = social_urls.get('vitals', '')
            enrichment.zocdoc_url = social_urls.get('zocdoc', '')
        
        enrichment.website_scraped = True
        enrichment.enrichment_sources = [website_url]
        
        social_count = len(social_urls) if enable_social else 0
        logger.info(f"Enriched {website_url}: {len(emails)} emails, {social_count} social links")
        
    except httpx.TimeoutException:
        enrichment.website_scrape_error = "Timeout"
        logger.warning(f"Timeout scraping {website_url}")
    except httpx.HTTPError as e:
        enrichment.website_scrape_error = f"HTTP error: {str(e)}"
        logger.warning(f"HTTP error scraping {website_url}: {e}")
    except Exception as e:
        enrichment.website_scrape_error = f"Error: {str(e)}"
        logger.error(f"Error scraping {website_url}: {e}")
    
    return enrichment


async def search_linkedin_profile(
    provider_name: str,
    city: str,
    state: str,
    credential: str,
    client: httpx.AsyncClient,
) -> str:
    """
    Search for LinkedIn profile URL for a provider.
    
    Args:
        provider_name: Provider's full name
        city: Practice city
        state: Practice state
        credential: Provider credential (MD, DO, NP, etc.)
        client: HTTP client
        
    Returns:
        LinkedIn profile URL if found, empty string otherwise
    """
    # PLACEHOLDER: LinkedIn profile search implementation
    # In production, this would:
    # 1. Use Google search with site:linkedin.com/in
    # 2. Parse search results
    # 3. Return best match
    
    # For now, return empty (feature coming soon)
    logger.info(f"LinkedIn search for {provider_name}: Feature coming soon")
    return ""
