"""Core scraping logic for NPI Healthcare Provider Scraper.

Queries the NPPES NPI Registry API v2.1 for healthcare provider data.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

import httpx

from .models import (
    AddressRecord,
    EndpointRecord,
    IdentifierRecord,
    OtherNameRecord,
    ProviderRecord,
    ScraperInput,
    TaxonomyRecord,
)
from .utils import (
    NPPES_API_URL,
    NPPES_API_VERSION,
    NPPES_MAX_PER_PAGE,
    RateLimiter,
    build_headers,
    fetch_json,
)

logger = logging.getLogger(__name__)


def _clean(value: str | None) -> str:
    """Clean a string value, stripping leading/trailing dashes and whitespace."""
    if not value or value == "--":
        return ""
    return value.strip()


def _normalize_provider(raw: dict[str, Any]) -> ProviderRecord:
    """Convert a raw NPPES API result to a ProviderRecord."""
    basic = raw.get("basic", {})
    enum_type = raw.get("enumeration_type", "")
    npi = str(raw.get("number", ""))

    # Addresses
    addresses = []
    for addr in raw.get("addresses", []):
        addresses.append(AddressRecord(
            address_purpose=addr.get("address_purpose", ""),
            address_1=addr.get("address_1", ""),
            address_2=addr.get("address_2", ""),
            city=addr.get("city", ""),
            state=addr.get("state", ""),
            postal_code=addr.get("postal_code", ""),
            country_code=addr.get("country_code", ""),
            country_name=addr.get("country_name", ""),
            telephone_number=addr.get("telephone_number", ""),
            fax_number=addr.get("fax_number", ""),
        ))

    # Taxonomies
    taxonomies = []
    primary_specialty = ""
    for tax in raw.get("taxonomies", []):
        desc = tax.get("desc", "") or ""
        taxonomies.append(TaxonomyRecord(
            code=tax.get("code", ""),
            description=desc,
            license=tax.get("license", "") or "",
            state=tax.get("state", "") or "",
            primary=bool(tax.get("primary", False)),
            taxonomy_group=tax.get("taxonomy_group", "") or "",
        ))
        if tax.get("primary"):
            primary_specialty = desc

    # Identifiers
    identifiers = []
    for ident in raw.get("identifiers", []):
        identifiers.append(IdentifierRecord(
            code=ident.get("code", ""),
            description=ident.get("desc", ""),
            identifier=ident.get("identifier", ""),
            state=ident.get("state", "") or "",
            issuer=ident.get("issuer", "") or "",
        ))

    # Other names
    other_names = []
    for name in raw.get("other_names", []):
        other_names.append(OtherNameRecord(
            type=name.get("type", ""),
            code=name.get("code", ""),
            first_name=_clean(name.get("first_name")),
            last_name=_clean(name.get("last_name")),
            middle_name=_clean(name.get("middle_name")),
            prefix=_clean(name.get("prefix")),
            suffix=_clean(name.get("suffix")),
            credential=_clean(name.get("credential")),
            organization_name=_clean(name.get("organization_name")),
        ))

    # Endpoints
    endpoints = []
    for ep in raw.get("endpoints", []):
        endpoints.append(EndpointRecord(
            endpoint_type=ep.get("endpointType", ""),
            endpoint_type_description=ep.get("endpointTypeDescription", ""),
            endpoint=ep.get("endpoint", ""),
            endpoint_description=ep.get("endpointDescription", ""),
            affiliation=ep.get("affiliation", ""),
            affiliation_name=ep.get("affiliationName", ""),
            use=ep.get("use", ""),
            use_description=ep.get("useDescription", ""),
            content_type=ep.get("contentType", ""),
            content_type_description=ep.get("contentTypeDescription", ""),
        ))

    # Practice address (LOCATION type)
    practice_city = ""
    practice_state = ""
    for addr in addresses:
        if addr.address_purpose == "LOCATION":
            practice_city = addr.city
            practice_state = addr.state
            break

    return ProviderRecord(
        npi_number=npi,
        enumeration_type=enum_type,
        # Individual
        first_name=_clean(basic.get("first_name")),
        last_name=_clean(basic.get("last_name")),
        middle_name=_clean(basic.get("middle_name")),
        name_prefix=_clean(basic.get("name_prefix")),
        name_suffix=_clean(basic.get("name_suffix")),
        credential=_clean(basic.get("credential")),
        sex=_clean(basic.get("sex")),
        sole_proprietor=_clean(basic.get("sole_proprietor")),
        # Organization
        organization_name=_clean(basic.get("organization_name")),
        organizational_subpart=_clean(basic.get("organizational_subpart")),
        authorized_official_first_name=_clean(basic.get("authorized_official_first_name")),
        authorized_official_last_name=_clean(basic.get("authorized_official_last_name")),
        authorized_official_title=_clean(basic.get("authorized_official_title_or_position")),
        authorized_official_telephone=_clean(basic.get("authorized_official_telephone_number")),
        # Dates
        enumeration_date=_clean(basic.get("enumeration_date")),
        last_updated=_clean(basic.get("last_updated")),
        certification_date=_clean(basic.get("certification_date")),
        status=_clean(basic.get("status")),
        # Sub-records
        addresses=addresses,
        taxonomies=taxonomies,
        identifiers=identifiers,
        other_names=other_names,
        endpoints=endpoints,
        # Convenience
        primary_specialty=primary_specialty,
        practice_address_city=practice_city,
        practice_address_state=practice_state,
        npi_registry_url=f"https://npiregistry.cms.hhs.gov/provider-view/{npi}" if npi else "",
    )


class NPIProviderScraper:
    """Async scraper for NPPES NPI Registry."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        config: ScraperInput,
    ) -> None:
        self.client = client
        self.rate_limiter = rate_limiter
        self.config = config
        self.headers = build_headers()
        self.timeout = float(config.timeout_secs)
        self.retries = config.max_retries

    def _build_params(self, skip: int = 0) -> dict[str, Any]:
        """Build NPPES API query parameters from config."""
        params: dict[str, Any] = {
            "version": NPPES_API_VERSION,
            "limit": min(NPPES_MAX_PER_PAGE, self.config.max_results - skip),
        }

        if skip > 0:
            params["skip"] = skip

        mode = self.config.mode.value

        if mode == "get_provider":
            params["number"] = self.config.npi_number
            return params

        if mode == "search_organizations":
            if self.config.organization_name:
                params["organization_name"] = self.config.organization_name
            elif self.config.query:
                params["organization_name"] = self.config.query
            params["enumeration_type"] = "NPI-2"

        elif mode == "search_by_specialty":
            if self.config.taxonomy_description:
                params["taxonomy_description"] = self.config.taxonomy_description
            elif self.config.query:
                params["taxonomy_description"] = self.config.query
            if self.config.enumeration_type:
                params["enumeration_type"] = self.config.enumeration_type

        else:  # search_providers
            if self.config.last_name:
                params["last_name"] = self.config.last_name
            elif self.config.query:
                params["last_name"] = self.config.query
            if self.config.first_name:
                params["first_name"] = self.config.first_name
            if self.config.npi_number:
                params["number"] = self.config.npi_number
            if self.config.enumeration_type:
                params["enumeration_type"] = self.config.enumeration_type
            else:
                # Default search_providers to individuals
                params["enumeration_type"] = "NPI-1"

        # Location filters (apply to all search modes)
        if self.config.city:
            params["city"] = self.config.city
        if self.config.state:
            params["state"] = self.config.state
        if self.config.postal_code:
            params["postal_code"] = self.config.postal_code
        if self.config.country_code:
            params["country_code"] = self.config.country_code

        return params

    async def scrape(self) -> AsyncGenerator[dict[str, Any], None]:
        """Main scrape entry point -- yields normalized provider dicts."""
        count = 0
        skip = 0

        while count < self.config.max_results:
            params = self._build_params(skip=skip)
            remaining = self.config.max_results - count
            params["limit"] = min(NPPES_MAX_PER_PAGE, remaining)

            data = await fetch_json(
                self.client,
                NPPES_API_URL,
                params,
                self.rate_limiter,
                self.headers,
                max_retries=self.retries,
                timeout=self.timeout,
            )

            if not data:
                break

            results = data.get("results", [])
            result_count = data.get("result_count", 0)

            if not results:
                break

            for raw_provider in results:
                if count >= self.config.max_results:
                    break
                record = _normalize_provider(raw_provider)
                yield record.model_dump()
                count += 1

            # Check if there are more pages
            if len(results) < params["limit"] or count >= result_count:
                break

            skip += len(results)

        logger.info(f"Scraped {count} providers total")
