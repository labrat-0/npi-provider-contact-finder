"""Tests for personalEmailsOnly filtering (name-in-localpart only)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.enrichment import _email_localpart_has_name, _filter_personal_emails  # noqa: E402


def test_localpart_name_match():
    # Keep: name in localpart
    assert _email_localpart_has_name("jsmith@clinic.com", "John", "Smith")
    assert _email_localpart_has_name("paula.cantu@med.com", "Paula", "Cantu")
    assert _email_localpart_has_name("drsmith@x.com", "John", "Smith")
    # Drop: generic role mailboxes
    assert not _email_localpart_has_name("info@smithfamilymed.com", "John", "Smith")
    assert not _email_localpart_has_name("billing@clinic.com", "John", "Smith")
    # Drop: name only in domain, not localpart
    assert not _email_localpart_has_name("contact@cantumed.com", "Paula", "Cantu")
    # Org record (no name) matches nothing
    assert not _email_localpart_has_name("info@org.com", "", "")
    # Short names (<3) don't match to avoid noise
    assert not _email_localpart_has_name("al@x.com", "Al", "Vo")


def test_filter_personal_emails():
    emails = [
        "jsmith@clinic.com",
        "info@clinic.com",
        "billing@clinic.com",
        "john.smith@clinic.com",
    ]
    kept = _filter_personal_emails(emails, "John", "Smith")
    assert kept == ["jsmith@clinic.com", "john.smith@clinic.com"], kept


if __name__ == "__main__":
    test_localpart_name_match()
    test_filter_personal_emails()
    print("PASS")
