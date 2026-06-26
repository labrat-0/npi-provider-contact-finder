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

# Social media URL patterns. NOTE: linkedin_profile_url is meant to be the
# provider's personal /in/ profile, so the linkedin pattern only matches /in/
# — a hospital's /company/ page must not be stored as the person's profile
# (it would also block the dedicated personal-profile search).
SOCIAL_PATTERNS = {
    'linkedin': re.compile(r'https?://(?:[\w.]+\.)?linkedin\.com/in/[\w-]+/?'),
    'facebook': re.compile(r'https?://(?:www\.)?facebook\.com/[\w.-]+/?'),
    'twitter': re.compile(r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+/?'),
    'instagram': re.compile(r'https?://(?:www\.)?instagram\.com/[\w.]+/?'),
    'healthgrades': re.compile(r'https?://(?:www\.)?healthgrades\.com/physician/[\w-]+'),
    'vitals': re.compile(r'https?://(?:www\.)?vitals\.com/doctors/[\w-]+'),
    'zocdoc': re.compile(r'https?://(?:www\.)?zocdoc\.com/doctor/[\w-]+'),
}

# Template/sample emails commonly embedded in site boilerplate. Scraping these
# produces junk leads (e.g. Cleveland Clinic pages carry "username@email.com").
_PLACEHOLDER_EMAIL_DOMAINS = frozenset([
    'example.com', 'example.org', 'example.net', 'email.com', 'domain.com',
    'yourdomain.com', 'test.com', 'sample.com', 'sentry.io', 'wixpress.com',
    'mapquest.com', 'godaddy.com', 'squarespace.com',
])
_PLACEHOLDER_EMAIL_LOCALPARTS = frozenset([
    'username', 'address', 'youremail', 'your-email', 'email', 'name',
    'user', 'example', 'firstname', 'lastname', 'no-reply', 'noreply',
    'sentry', 'you',
])


def _extract_emails_from_text(text: str) -> list[str]:
    """Extract unique email addresses from text, skipping placeholders."""
    matches = EMAIL_PATTERN.findall(text)
    emails = []
    for email in matches:
        lower_email = email.lower()
        # Skip image extensions and common false positives
        if any(lower_email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
            continue
        if '@' not in email or '.' not in email.split('@')[1]:
            continue
        localpart, _, domain = lower_email.partition('@')
        if domain in _PLACEHOLDER_EMAIL_DOMAINS:
            continue
        if localpart in _PLACEHOLDER_EMAIL_LOCALPARTS:
            continue
        emails.append(email)
    return list(set(emails))


# Generic role mailboxes legitimately belonging to a practice (not a specific
# different person). These are kept even when they don't match the provider's
# name, since they're the practice's own shared inbox.
_GENERIC_EMAIL_LOCALPARTS = frozenset([
    'info', 'contact', 'contactus', 'hello', 'office', 'admin',
    'administrator', 'reception', 'frontdesk', 'frontoffice', 'appointments',
    'appointment', 'scheduling', 'schedule', 'billing', 'accounts',
    'accounting', 'support', 'help', 'care', 'patient', 'patients',
    'newpatients', 'referral', 'referrals', 'records', 'medicalrecords',
    'practice', 'clinic', 'mail', 'email', 'general', 'inquiries', 'inquiry',
])


def _alpha(s: str) -> str:
    """Lowercase, strip to a-z only."""
    return re.sub(r'[^a-z]', '', s.lower())


def _email_belongs_to_provider(
    email: str, first: str, last: str, website_url: str = ""
) -> bool:
    """
    Strict check that an email plausibly belongs to the searched provider.

    Prevents wrong-person leaks (e.g. ``zach.carlyle@iowa.gov`` returned for
    provider "Paula Cantu"). Keeps an email only when at least one holds:
      * the email's host (sans TLD) contains the provider's last name — i.e. a
        practice-owned domain like ``cantufamilymedicine.com``;
      * the localpart contains the provider's first or last name;
      * the localpart is a generic practice role mailbox (info@, contact@, ...).
    Org records (no first/last) keep everything — there is no name to match.
    Precision over recall: a dropped legit email is better than a wrong person.
    """
    first_a = _alpha(first)
    last_a = _alpha(last)
    if not first_a and not last_a:
        return True  # organization record — nothing to match against

    localpart = email.lower().partition('@')[0]
    local_a = _alpha(localpart)

    # Generic role mailbox: keep (practice's own inbox).
    bare = re.sub(r'[^a-z0-9]', '', localpart.lower())
    bare_alpha = re.sub(r'[0-9]', '', bare)
    if bare_alpha in _GENERIC_EMAIL_LOCALPARTS:
        return True

    # Name appears in localpart (require >=3 chars to avoid noise matches).
    if len(last_a) >= 3 and last_a in local_a:
        return True
    if len(first_a) >= 3 and first_a in local_a:
        return True

    # Practice-owned domain carrying the provider's last name.
    if last_a and len(last_a) >= 3 and website_url:
        host = urlparse(
            website_url if '://' in website_url else 'https://' + website_url
        ).netloc.lower()
        host_alpha = _alpha(host.rsplit('.', 1)[0])  # drop TLD
        if last_a in host_alpha:
            return True

    return False


def _filter_emails_by_provider(
    emails: list[str], first: str, last: str, website_url: str = ""
) -> list[str]:
    """Drop emails that don't plausibly belong to the provider (see above)."""
    return [e for e in emails if _email_belongs_to_provider(e, first, last, website_url)]


def _email_localpart_has_name(email: str, first: str, last: str) -> bool:
    """
    True if the email's localpart contains the provider's first or last name
    (>=3 chars). This is the strict "personal" test for ``personalEmailsOnly``:
    keep ``paula.cantu@`` / ``jsmith@`` but drop generic role mailboxes
    (``info@``, ``billing@``) and name-matched-domain-only addresses
    (``info@cantumed.com``). Org records (no name) match nothing.
    """
    local_a = _alpha(email.partition('@')[0])
    first_a = _alpha(first)
    last_a = _alpha(last)
    if len(last_a) >= 3 and last_a in local_a:
        return True
    if len(first_a) >= 3 and first_a in local_a:
        return True
    return False


def _filter_personal_emails(
    emails: list[str], first: str, last: str
) -> list[str]:
    """Keep only emails whose localpart carries the provider's name."""
    return [e for e in emails if _email_localpart_has_name(e, first, last)]


# Per-run cache of domain -> has-MX-record, so we resolve each mail domain once.
_MX_CACHE: dict[str, bool] = {}


def _domain_has_mx(domain: str) -> bool:
    """
    True if the domain has a deliverable mail setup (MX, or A as RFC-5321
    fallback). Result cached per domain for the process. DNS-only — no SMTP
    handshake, so it is fast and never touches the recipient's mail server.
    Returns False on any resolver error (treat unverifiable as unverified).
    """
    domain = domain.lower().strip()
    if not domain:
        return False
    if domain in _MX_CACHE:
        return _MX_CACHE[domain]

    ok = False
    try:
        import dns.resolver  # dnspython; optional dependency

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5.0
        resolver.timeout = 5.0
        try:
            answers = resolver.resolve(domain, "MX")
            ok = len(answers) > 0
        except dns.resolver.NoAnswer:
            # No MX is valid per RFC 5321 if an A/AAAA record exists.
            try:
                resolver.resolve(domain, "A")
                ok = True
            except Exception:
                ok = False
    except Exception as e:  # ImportError or any DNS failure -> unverified
        logger.debug(f"MX check unavailable/failed for {domain}: {e}")
        ok = False

    _MX_CACHE[domain] = ok
    return ok


def _verify_emails(emails: list[str]) -> list[str]:
    """Return the subset of emails whose domain passes the MX deliverability
    check. Used to bill verified-email vs email-found (charge-on-success)."""
    verified = []
    for email in emails:
        domain = email.rpartition("@")[2]
        if domain and _domain_has_mx(domain):
            verified.append(email)
    return verified


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


# Domains to skip when evaluating search results.
# These are directories / aggregators, not practice websites.
_DIRECTORY_DOMAINS = frozenset([
    'healthgrades.com', 'vitals.com', 'zocdoc.com', 'doximity.com',
    'webmd.com', 'ratemds.com', 'yelp.com', 'yellowpages.com',
    'betterdoctor.com', 'castlighthealth.com', 'usnews.com',
    'npiprofile.com', 'npino.com', 'medicare.gov', 'cms.gov',
    'facebook.com', 'twitter.com', 'x.com', 'linkedin.com',
    'instagram.com', 'bing.com', 'google.com', 'duckduckgo.com',
    'wikipedia.org', 'wikimedia.org',
    # Provider-directory / aggregator sites (no scrapeable practice contacts)
    'npidb.org', 'mapquest.com', 'healthlynked.com', 'everydayhealth.care',
    'everydayhealth.com', 'sharecare.com', 'md.com', 'wellness.com',
    'caredash.com', 'findatopdoc.com', 'docinfo.org',
    'medifind.com', 'getluna.com', 'doctor.com', 'healthcare4ppl.com',
    'ratemymd.com', 'opencare.com', 'solvhealth.com',
])

# URL path markers for health-system / hospital "find a doctor" directory
# listings. These pages (e.g. ascension.org/find-care/provider/...) are
# provider lookups, not a practice's own site, and rarely carry scrapeable
# emails — skip them and keep looking for the real site. Path-based so it
# generalizes across every health system instead of a domain allowlist.
_DIRECTORY_PATH_MARKERS = (
    '/find-care', '/find-a-doctor', '/find-a-physician', '/find-a-provider',
    '/findadoctor', '/find_a_doctor', '/finddoctor', '/doctor-search',
    '/provider-search', '/physician-finder', '/our-providers', '/our-doctors',
)


def _is_directory_url(href: str) -> bool:
    """True if the URL is a known directory domain or a provider-finder path."""
    parsed = urlparse(href)
    domain = parsed.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    # Government / military hosts (e.g. state licensing boards, iowa.gov) are
    # shared institutional directories listing many people — scraping them
    # yields a different person's email than the searched provider. Skip them.
    host = domain.split(':')[0]
    if host.endswith('.gov') or host.endswith('.mil') or host == 'gov' or host == 'mil':
        return True
    if any(domain == d or domain.endswith('.' + d) for d in _DIRECTORY_DOMAINS):
        return True
    path = parsed.path.lower()
    return any(marker in path for marker in _DIRECTORY_PATH_MARKERS)


# Google's own hosts (search chrome, footer, infra) across all TLDs/subdomains.
_GOOGLE_HOST = re.compile(
    r'(^|\.)(google\.[a-z.]+|gstatic\.com|googleusercontent\.com|'
    r'googleapis\.com|googleadservices\.com|youtube\.com)$',
    re.I,
)


async def _google_search(
    query: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
) -> tuple[list[str], str | None]:
    """
    Run a Google web search and return organic result URLs.

    The client is expected to be routed through Apify Proxy (Google SERP group);
    public search engines block datacenter IPs directly.

    Args:
        query: Search query string
        client: HTTP client (should be proxied for reliable results)
        rate_limiter: Rate limiter
        timeout: Request timeout in seconds

    Returns:
        Tuple of (ordered list of result URLs, error message or None).
        An empty list with error=None means the search succeeded but matched
        nothing; a non-None error means the search itself failed (block,
        timeout, non-200) and the caller should not treat it as "no website".
    """
    from urllib.parse import parse_qs

    # NOTE: target URL is HTTP, not HTTPS. Apify's Google SERP proxy only
    # serves plain-HTTP requests (absolute-form through the proxy); an HTTPS
    # target forces a CONNECT tunnel the SERP proxy rejects with 400. Over a
    # direct (non-proxy) connection Google simply redirects HTTP -> HTTPS.
    search_url = "http://www.google.com/search?" + urlencode(
        {"q": query, "num": "10", "hl": "en"}
    )

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
            return [], f"Search failed (HTTP {response.status_code})"

        soup = BeautifulSoup(response.text, "html.parser")

        urls: list[str] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Google wraps organic results as /url?q=<target>&...
            if href.startswith("/url?"):
                target = parse_qs(urlparse(href).query).get("q", [""])[0]
                if target:
                    href = target
            if not href.startswith(("http://", "https://")):
                continue
            domain = urlparse(href).netloc.lower()
            # Skip Google's own chrome/footer links. The SERP proxy returns
            # localized Google domains (google.ae, google.com.br, google.co.uk,
            # ...), so a plain "endswith google.com" check misses them and the
            # footer "about/products" link gets picked as a fake result.
            if _GOOGLE_HOST.search(domain):
                continue
            if href not in seen:
                seen.add(href)
                urls.append(href)

        return urls, None

    except httpx.TimeoutException:
        return [], "Search timed out"
    except httpx.HTTPError as e:
        return [], f"Search HTTP error: {e}"
    except Exception as e:
        return [], f"Search error: {e}"


async def _discover_practice_website(
    provider_name: str,
    city: str,
    state: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
) -> tuple[str, str | None]:
    """
    Discover a practice website URL using Google web search.

    Args:
        provider_name: Provider full name (individual) or organization name
        city: Practice city
        state: Practice state abbreviation (e.g. "NY")
        client: HTTP client (proxied for search)
        rate_limiter: Rate limiter
        timeout: Request timeout in seconds

    Returns:
        Tuple of (website URL or "", error message or None). A non-None error
        means the search itself failed, as opposed to genuinely finding nothing.
    """
    if not provider_name:
        return "", None

    # Build a specific search query
    query_parts = [provider_name]
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query_parts.append("medical practice")
    query = " ".join(query_parts)

    urls, error = await _google_search(query, client, rate_limiter, timeout)
    if error:
        logger.warning(f"Website discovery search failed for {provider_name}: {error}")
        return "", error

    for href in urls:
        # Skip directory/aggregator sites and provider-finder listing pages
        if _is_directory_url(href):
            continue
        # Skip non-HTML documents (PDFs etc.) — these are CVs/rosters/news with
        # no scrapeable contact form and rarely a usable email.
        path = urlparse(href).path.lower()
        if path.endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx')):
            continue

        logger.info(f"Website discovery found: {href} for provider {provider_name}")
        return href, None

    logger.info(f"Website discovery: no result found for {provider_name} in {city}, {state}")
    return "", None


# Org-name suffixes that don't belong in a domain guess.
_ORG_DOMAIN_STOPWORDS = frozenset([
    'llc', 'pllc', 'inc', 'pc', 'pa', 'pllp', 'llp', 'ltd', 'corp',
    'the', 'and', 'of', 'a',
])


def _domain_candidates(org_name: str) -> list[str]:
    """
    Build a few plausible domain guesses from an organization name.

    "Cantu Family Medicine PLLC" -> ["cantufamilymedicine.com",
    "cantufamilymedicine.org", "cantufamilymedicine.net"]. Returns [] when the
    name is too short/generic to guess safely (precision over recall).
    """
    words = [
        re.sub(r'[^a-z0-9]', '', w.lower())
        for w in org_name.split()
    ]
    words = [w for w in words if w and w not in _ORG_DOMAIN_STOPWORDS]
    if not words:
        return []
    slug = ''.join(words)
    # Too short -> too generic (risk of squatters / wrong site). Skip.
    if len(slug) < 8:
        return []
    return [f"{slug}.com", f"{slug}.org", f"{slug}.net"]


async def _guess_practice_domain(
    org_name: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
) -> str:
    """
    Try to resolve a practice website by guessing its domain and fetching it
    directly (no proxy, no paid SERP). Returns the live URL on a confident hit,
    else "". Free skip-SERP waterfall stage: most branded practices own the
    obvious domain, so this avoids a paid search for them.
    """
    for candidate in _domain_candidates(org_name):
        url = "https://" + candidate
        try:
            await rate_limiter.wait()
            resp = await client.get(
                url,
                timeout=timeout,
                follow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; NPIContactFinder/1.0)'},
            )
            if resp.status_code != 200:
                continue
            if 'html' not in resp.headers.get('content-type', '').lower():
                continue
            final_url = str(resp.url)
            if _is_directory_url(final_url):
                continue
            logger.info(f"Domain-guess hit for {org_name!r}: {final_url}")
            return final_url
        except Exception:
            continue
    return ""


async def enrich_provider_contacts(
    provider_data: dict[str, Any],
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
    enable_linkedin: bool = False,
    enable_social: bool = False,
    search_client: httpx.AsyncClient | None = None,
    website_cache: dict[tuple[str, str, str], str] | None = None,
    personal_emails_only: bool = False,
) -> ContactEnrichment:
    """
    Enrich provider with contact information from practice website.

    Args:
        provider_data: Provider record from NPPES
        client: HTTP client for scraping practice websites
        rate_limiter: Rate limiter for requests
        timeout: Timeout for website scraping (seconds)
        enable_linkedin: Whether to search for LinkedIn profiles
        enable_social: Whether to extract all social media URLs
        search_client: HTTP client for web search (proxied). Falls back to
            ``client`` when not provided.
        website_cache: Optional per-run cache mapping (name, city, state) to the
            discovered website URL. Avoids re-running the paid website-discovery
            SERP for providers that share the same name/location (e.g. multiple
            records for one practice). A cached "" means "searched, none found".

    Returns:
        ContactEnrichment record with discovered contacts
    """
    search_client = search_client or client

    enrichment = ContactEnrichment(
        enrichment_timestamp=datetime.utcnow().isoformat() + 'Z'
    )

    # Raw NPPES results nest provider names under "basic" and use "number"
    # for the NPI. Fall back to flat keys so normalized records also work.
    basic = provider_data.get('basic', {})
    npi = str(provider_data.get('number', '') or provider_data.get('npi_number', ''))

    # Provider name + location, reused for website and LinkedIn search.
    first = basic.get('first_name', '') or provider_data.get('first_name', '')
    last = basic.get('last_name', '') or provider_data.get('last_name', '')
    org = basic.get('organization_name', '') or provider_data.get('organization_name', '')
    provider_name = (f"{first} {last}".strip()) if (first or last) else org
    credential = basic.get('credential', '') or provider_data.get('credential', '')
    city = ''
    state = ''
    for addr in provider_data.get('addresses', []):
        if addr.get('address_purpose') == 'LOCATION':
            city = addr.get('city', '')
            state = addr.get('state', '')
            break
    if not city and provider_data.get('addresses'):
        city = provider_data['addresses'][0].get('city', '')
        state = provider_data['addresses'][0].get('state', '')

    # --- Step 1: Check if provider already has a website URL in endpoints ---
    # NPPES endpoints are mostly FHIR API URLs and DIRECT secure-messaging
    # addresses, neither of which is a practice website. Only consider
    # endpoint types that could be a real site.
    practice_website = ""
    for endpoint in provider_data.get('endpoints', []):
        ep_value = endpoint.get('endpoint', '')
        ep_type = (
            endpoint.get('endpointType', '')
            or endpoint.get('endpoint_type', '')
        ).upper()
        if ep_type in ('FHIR', 'DIRECT', 'REST', 'SOAP', 'OTHER'):
            continue
        if ep_value and ('http' in ep_value or 'www.' in ep_value):
            parsed = urlparse(ep_value if '://' in ep_value else 'https://' + ep_value)
            # Require a real host — guards against malformed NPPES endpoint
            # values like "https:/host/..." (single slash) that parse with an
            # empty netloc and are not usable URLs.
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                practice_website = ep_value
                logger.info(f"NPI {npi}: using website from endpoints field: {practice_website}")
                break

    # --- Step 2: Discover website via search if not already found ---
    discovery_error: str | None = None
    if not practice_website and provider_name:
        # Reuse a prior discovery result for the same (name, city, state) to
        # avoid paying for a duplicate website-discovery SERP within one run.
        cache_key = (provider_name.lower(), city.lower(), state.lower())
        if website_cache is not None and cache_key in website_cache:
            practice_website = website_cache[cache_key]
            logger.info(
                f"Website discovery cache hit for {provider_name} "
                f"({city}, {state}): {practice_website or 'no website'}"
            )
        else:
            # Stage 3 (free): guess the org's domain and fetch it directly — no
            # proxy, no paid SERP. Only for org-named records (individual-name
            # guesses are too noisy). Falls through to paid search on miss.
            if org:
                practice_website = await _guess_practice_domain(
                    org, client, rate_limiter, timeout
                )
            # Stage 4 (paid): Google SERP, last resort.
            if not practice_website:
                practice_website, discovery_error = await _discover_practice_website(
                    provider_name=provider_name,
                    city=city,
                    state=state,
                    client=search_client,
                    rate_limiter=rate_limiter,
                    timeout=timeout,
                )
            # Cache only successful resolutions (error=None); a failed search
            # (block/timeout) should be retried for the next provider.
            if website_cache is not None and discovery_error is None:
                website_cache[cache_key] = practice_website

    # --- Step 3: Scrape the discovered website ---
    if practice_website:
        enrichment = await enrich_provider_website(
            website_url=practice_website,
            client=client,
            rate_limiter=rate_limiter,
            timeout=timeout,
            enable_social=enable_social,
            first_name=first,
            last_name=last,
            personal_emails_only=personal_emails_only,
        )
        # Ensure enrichment_sources includes the discovered URL
        if practice_website not in enrichment.enrichment_sources:
            enrichment.enrichment_sources = [practice_website] + enrichment.enrichment_sources
    elif discovery_error:
        # The search itself failed (block/timeout) — distinct from "no website".
        enrichment.website_scraped = False
        enrichment.website_scrape_error = f"Website search failed: {discovery_error}"
        logger.warning(f"Contact enrichment for NPI {npi}: {discovery_error}")
    else:
        enrichment.website_scraped = False
        enrichment.website_scrape_error = "No practice website found"
        logger.info(f"Contact enrichment for NPI {npi}: no website discovered")

    # NOTE: paid LinkedIn profile search was removed — it required a second
    # paid SERP per provider and could not be priced profitably. Any LinkedIn
    # URL still comes free from the scraped website HTML (see enrich_provider_website),
    # as an unbilled bonus field.

    return enrichment


async def enrich_provider_website(
    website_url: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
    enable_social: bool = True,
    first_name: str = "",
    last_name: str = "",
    personal_emails_only: bool = False,
) -> ContactEnrichment:
    """
    Scrape a practice website for contact information.

    Args:
        website_url: Practice website URL
        client: HTTP client
        rate_limiter: Rate limiter
        timeout: Request timeout
        enable_social: Whether to extract social media links
        first_name: Provider first name, used to drop wrong-person emails
        last_name: Provider last name, used to drop wrong-person emails
        personal_emails_only: keep only emails whose localpart carries the
            provider's name (drop generic role mailboxes)

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
        
        # Extract emails, then drop any that don't plausibly belong to this
        # provider (guards against shared/institutional pages leaking a
        # different person's address, e.g. zach.carlyle@iowa.gov for "Paula Cantu").
        raw_emails = _extract_emails_from_text(html)
        emails = _filter_emails_by_provider(raw_emails, first_name, last_name, website_url)
        # Optionally narrow to the named provider's own mailbox (drop info@ etc.).
        if personal_emails_only:
            emails = _filter_personal_emails(emails, first_name, last_name)
        enrichment.emails = emails
        # MX-verify for charge-on-success billing (verified-email vs email-found).
        enrichment.verified_emails = _verify_emails(emails)
        # Observability: distinguish "page had no emails" from "name filter
        # dropped them all". If many are dropped, discovery may be landing on
        # shared/roster pages (expected) — or the filter is too strict (bug).
        if raw_emails:
            logger.info(
                f"Email extraction for {website_url}: "
                f"{len(raw_emails)} found on page, {len(emails)} kept after "
                f"provider name-match filter "
                f"({len(raw_emails) - len(emails)} dropped as unrelated/placeholder)."
            )
        
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


# Matches a LinkedIn member profile URL (linkedin.com/in/<slug>)
_LINKEDIN_PROFILE = re.compile(r'^https?://(?:[\w.]+\.)?linkedin\.com/in/[\w%-]+', re.I)


def _linkedin_slug_matches_name(href: str, first: str, last: str) -> bool:
    """
    True if the LinkedIn profile slug plausibly belongs to this provider.

    LinkedIn member slugs are typically ``firstname-lastname-<hash>``. We
    require BOTH the first and last name (alpha-only) to appear in the slug,
    rejecting wrong-person matches like ``richard-pilcher`` for a provider
    named William Pilcher. Conservative by design: precision over recall.
    """
    first_a = re.sub(r'[^a-z]', '', first.lower())
    last_a = re.sub(r'[^a-z]', '', last.lower())
    if not first_a or not last_a:
        return False
    # Slug only (path after /in/), alpha-only.
    path = urlparse(href).path
    slug = path[path.lower().find('/in/') + 4:] if '/in/' in path.lower() else path
    slug_a = re.sub(r'[^a-z]', '', slug.lower())
    return first_a in slug_a and last_a in slug_a


async def search_linkedin_profile(
    provider_name: str,
    city: str,
    state: str,
    credential: str,
    client: httpx.AsyncClient,
    rate_limiter: RateLimiter,
    timeout: int = 10,
    first_name: str = "",
    last_name: str = "",
) -> str:
    """
    Search for a provider's LinkedIn profile URL via Google web search.

    Args:
        provider_name: Provider's full name
        city: Practice city
        state: Practice state
        credential: Provider credential (MD, DO, NP, etc.)
        client: HTTP client (proxied for search)
        rate_limiter: Rate limiter
        timeout: Request timeout in seconds

    Returns:
        LinkedIn profile URL if found, empty string otherwise
    """
    if not provider_name:
        return ""

    query_parts = ["site:linkedin.com/in", provider_name]
    if credential:
        query_parts.append(credential)
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query = " ".join(query_parts)

    urls, error = await _google_search(query, client, rate_limiter, timeout)
    if error:
        logger.warning(f"LinkedIn search failed for {provider_name}: {error}")
        return ""

    # If we have first/last names, require the slug to match to avoid
    # wrong-person matches. Fall back to first-result only when names are
    # unavailable (e.g. organization records).
    verify = bool(first_name and last_name)

    for href in urls:
        match = _LINKEDIN_PROFILE.match(href)
        if not match:
            continue
        if verify and not _linkedin_slug_matches_name(href, first_name, last_name):
            continue
        # Strip query string / tracking params, keep the canonical profile URL.
        profile_url = href.split("?")[0]
        logger.info(f"LinkedIn profile found for {provider_name}: {profile_url}")
        return profile_url

    logger.info(f"LinkedIn search: no confident profile match for {provider_name}")
    return ""
