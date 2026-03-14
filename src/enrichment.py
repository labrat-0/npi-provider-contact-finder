"""Contact enrichment module for NPI Provider Contact Finder.

Scrapes practice websites for email addresses, social media profiles,
and additional contact information.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

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
    
    # Extract practice website from addresses (phone records sometimes have it)
    # Or from endpoints
    practice_website = ""
    
    # Check addresses for websites in fax/phone fields (sometimes providers put URLs there)
    for addr in provider_data.get('addresses', []):
        if addr.get('address_purpose') == 'LOCATION':
            # NPPES doesn't store websites in address records, but we can construct search URLs
            pass
    
    # For this implementation, we'll use Google search or direct website construction
    # In production, you'd want to:
    # 1. Search Google for "[provider name] [city] [state] medical practice"
    # 2. Extract website from search results
    # 3. Scrape that website
    
    # For now, we'll demonstrate the enrichment structure without actual HTTP calls
    # to avoid external dependencies during initial build
    
    # PLACEHOLDER: In production, implement website discovery + scraping here
    # Example implementation would be:
    # 1. Build search query from provider name + address
    # 2. Search Google or use a search API
    # 3. Extract website URL from results
    # 4. Scrape website for emails and social links
    
    logger.info(f"Contact enrichment for NPI {provider_data.get('npi_number')}: Website discovery not yet implemented")
    
    enrichment.website_scraped = False
    enrichment.website_scrape_error = "Website discovery feature coming soon"
    enrichment.enrichment_sources = ["placeholder"]
    
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
        
        logger.info(f"Enriched {website_url}: {len(emails)} emails, {len(social_urls) if enable_social else 0} social links")
        
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
