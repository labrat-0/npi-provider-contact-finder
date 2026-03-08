"""Pydantic models for NPI Provider Contact Finder."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScrapingMode(str, Enum):
    SEARCH_PROVIDERS = "search_providers"
    GET_PROVIDER = "get_provider"
    SEARCH_ORGANIZATIONS = "search_organizations"
    SEARCH_BY_SPECIALTY = "search_by_specialty"


class ScraperInput(BaseModel):
    mode: ScrapingMode = ScrapingMode.SEARCH_PROVIDERS
    query: str = ""
    npi_number: str = ""
    first_name: str = ""
    last_name: str = ""
    organization_name: str = ""
    taxonomy_description: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country_code: str = ""
    enumeration_type: str = ""  # NPI-1 or NPI-2
    max_results: int = 100
    request_interval_secs: float = 0.5
    timeout_secs: int = 30
    max_retries: int = 5
    
    # Contact enrichment options
    enable_email_enrichment: bool = False
    enable_linkedin_enrichment: bool = False
    enable_social_media_enrichment: bool = False
    email_enrichment_timeout: int = 10  # seconds per website scrape

    @classmethod
    def from_actor_input(cls, raw: dict[str, Any]) -> ScraperInput:
        return cls(
            mode=raw.get("mode", ScrapingMode.SEARCH_PROVIDERS),
            query=raw.get("query", ""),
            npi_number=raw.get("npiNumber", "") or raw.get("npi_number", ""),
            first_name=raw.get("firstName", "") or raw.get("first_name", ""),
            last_name=raw.get("lastName", "") or raw.get("last_name", ""),
            organization_name=raw.get("organizationName", "") or raw.get("organization_name", ""),
            taxonomy_description=raw.get("taxonomyDescription", "") or raw.get("taxonomy_description", ""),
            city=raw.get("city", ""),
            state=raw.get("state", ""),
            postal_code=raw.get("postalCode", "") or raw.get("postal_code", ""),
            country_code=raw.get("countryCode", "") or raw.get("country_code", ""),
            enumeration_type=raw.get("enumerationType", "") or raw.get("enumeration_type", ""),
            max_results=raw.get("maxResults", 100),
            request_interval_secs=raw.get("requestIntervalSecs", 0.5),
            timeout_secs=raw.get("timeoutSecs", 30),
            max_retries=raw.get("maxRetries", 5),
            enable_email_enrichment=raw.get("enableEmailEnrichment", False),
            enable_linkedin_enrichment=raw.get("enableLinkedInEnrichment", False),
            enable_social_media_enrichment=raw.get("enableSocialMediaEnrichment", False),
            email_enrichment_timeout=raw.get("emailEnrichmentTimeout", 10),
        )

    def validate_for_mode(self) -> str | None:
        if self.mode == ScrapingMode.GET_PROVIDER:
            if not self.npi_number:
                return "Provide an NPI number for get_provider mode."
            if not self.npi_number.isdigit() or len(self.npi_number) != 10:
                return "NPI number must be exactly 10 digits."
        if self.mode == ScrapingMode.SEARCH_PROVIDERS:
            if not (self.query or self.first_name or self.last_name or self.npi_number):
                return "Provide at least one of: query (last name), first name, or last name for search_providers."
        if self.mode == ScrapingMode.SEARCH_ORGANIZATIONS:
            if not (self.organization_name or self.query):
                return "Provide an organization name or query for search_organizations."
        if self.mode == ScrapingMode.SEARCH_BY_SPECIALTY:
            if not (self.taxonomy_description or self.query):
                return "Provide a taxonomy/specialty description for search_by_specialty."
        return None


class AddressRecord(BaseModel):
    """Provider address."""
    address_purpose: str = ""  # MAILING or LOCATION
    address_1: str = ""
    address_2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country_code: str = ""
    country_name: str = ""
    telephone_number: str = ""
    fax_number: str = ""


class TaxonomyRecord(BaseModel):
    """Provider taxonomy/specialty."""
    code: str = ""
    description: str = ""
    license: str = ""
    state: str = ""
    primary: bool = False
    taxonomy_group: str = ""


class IdentifierRecord(BaseModel):
    """Other provider identifiers."""
    code: str = ""
    description: str = ""
    identifier: str = ""
    state: str = ""
    issuer: str = ""


class OtherNameRecord(BaseModel):
    """Other names used by the provider."""
    name_type: str = ""
    code: str = ""
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    prefix: str = ""
    suffix: str = ""
    credential: str = ""
    organization_name: str = ""


class EndpointRecord(BaseModel):
    """Provider endpoint (e.g., Direct address, FHIR endpoint)."""
    endpoint_type: str = ""
    endpoint_type_description: str = ""
    endpoint: str = ""
    endpoint_description: str = ""
    affiliation: str = ""
    affiliation_name: str = ""
    use: str = ""
    use_description: str = ""
    content_type: str = ""
    content_type_description: str = ""


class ContactEnrichment(BaseModel):
    """Contact enrichment data from practice websites and social media."""
    
    # Email contacts
    emails: list[str] = Field(default_factory=list)
    primary_email: str = ""
    office_email: str = ""
    billing_email: str = ""
    
    # Website data
    practice_website: str = ""
    website_scraped: bool = False
    website_scrape_error: str = ""
    
    # Social media
    linkedin_profile_url: str = ""
    facebook_url: str = ""
    twitter_url: str = ""
    instagram_url: str = ""
    healthgrades_url: str = ""
    vitals_url: str = ""
    zocdoc_url: str = ""
    
    # Additional contacts
    office_manager_name: str = ""
    office_manager_email: str = ""
    billing_contact_email: str = ""
    
    # Enrichment metadata
    enrichment_timestamp: str = ""
    enrichment_sources: list[str] = Field(default_factory=list)


class ProviderRecord(BaseModel):
    """Normalized NPI provider record with contact enrichment."""

    schema_version: str = "2.0"  # Updated for contact finder
    record_type: str = "provider_with_contacts"

    # NPI
    npi_number: str = ""
    enumeration_type: str = ""  # NPI-1 (individual) or NPI-2 (organization)

    # Individual provider fields
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    name_prefix: str = ""
    name_suffix: str = ""
    credential: str = ""
    sex: str = ""
    sole_proprietor: str = ""

    # Organization fields
    organization_name: str = ""
    organizational_subpart: str = ""
    authorized_official_first_name: str = ""
    authorized_official_last_name: str = ""
    authorized_official_title: str = ""
    authorized_official_telephone: str = ""

    # Dates
    enumeration_date: str = ""
    last_updated: str = ""
    certification_date: str = ""
    status: str = ""

    # Structured sub-records
    addresses: list[AddressRecord] = Field(default_factory=list)
    taxonomies: list[TaxonomyRecord] = Field(default_factory=list)
    identifiers: list[IdentifierRecord] = Field(default_factory=list)
    other_names: list[OtherNameRecord] = Field(default_factory=list)
    endpoints: list[EndpointRecord] = Field(default_factory=list)

    # Convenience
    primary_specialty: str = ""
    practice_address_city: str = ""
    practice_address_state: str = ""
    npi_registry_url: str = ""
    
    # Contact enrichment (optional, based on input settings)
    contact_enrichment: ContactEnrichment | None = None
