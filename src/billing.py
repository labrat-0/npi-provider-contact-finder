"""Charge-on-success billing for pay-per-event monetization.

The actor bills the customer only for values that actually appear in a written
output record. ``events_for_record`` is a pure function (no Apify dependency) so
it can be unit-tested in isolation; ``main`` awaits ``Actor.charge`` for each
returned event id and respects the customer's max-charge budget.

Event ids MUST match the Apify Console monetization config exactly:
    provider-record   any NPPES result returned
    phone-found       record carries a phone number (already in NPPES data)
    email-found       record has >=1 usable email, none verified
    verified-email    record has >=1 MX-verified email (instead of email-found)
"""

from __future__ import annotations

from typing import Any

EVENT_PROVIDER_RECORD = "provider-record"
EVENT_PHONE_FOUND = "phone-found"
EVENT_EMAIL_FOUND = "email-found"
EVENT_VERIFIED_EMAIL = "verified-email"


def _record_has_phone(record: dict[str, Any]) -> bool:
    """True if the record carries any phone number from NPPES base data."""
    if record.get("authorized_official_telephone"):
        return True
    for addr in record.get("addresses") or []:
        if isinstance(addr, dict) and addr.get("telephone_number"):
            return True
    return False


def events_for_record(record: dict[str, Any]) -> list[str]:
    """
    Return the billable event ids a written record earns, charge-on-success.

    Always charges ``provider-record`` (the customer received a real NPPES row).
    Adds ``phone-found`` when a phone is present. Adds exactly one email event:
    ``verified-email`` if any email passed verification, else ``email-found`` if
    any usable email is present, else neither. Never charges for a value the
    record does not actually contain.
    """
    events = [EVENT_PROVIDER_RECORD]

    if _record_has_phone(record):
        events.append(EVENT_PHONE_FOUND)

    enrichment = record.get("contact_enrichment") or {}
    if isinstance(enrichment, dict):
        verified = enrichment.get("verified_emails") or []
        emails = enrichment.get("emails") or []
        if verified:
            events.append(EVENT_VERIFIED_EMAIL)
        elif emails:
            events.append(EVENT_EMAIL_FOUND)

    return events
