"""Tests for charge-on-success billing event selection.

Pure-function tests — no Apify/network deps. Run with:
    python -m tests.test_billing
or under pytest if available.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.billing import events_for_record  # noqa: E402


CASES = [
    ("base only", {"addresses": []}, ["provider-record"]),
    (
        "phone via address",
        {"addresses": [{"telephone_number": "555-1212"}]},
        ["provider-record", "phone-found"],
    ),
    (
        "phone via authorized official",
        {"authorized_official_telephone": "555-0000"},
        ["provider-record", "phone-found"],
    ),
    (
        "unverified email -> email-found",
        {"contact_enrichment": {"emails": ["a@b.com"], "verified_emails": []}},
        ["provider-record", "email-found"],
    ),
    (
        "verified email replaces email-found",
        {"contact_enrichment": {"emails": ["a@b.com"], "verified_emails": ["a@b.com"]}},
        ["provider-record", "verified-email"],
    ),
    (
        "phone + verified email",
        {
            "addresses": [{"telephone_number": "5"}],
            "contact_enrichment": {"emails": ["a@b.com"], "verified_emails": ["a@b.com"]},
        },
        ["provider-record", "phone-found", "verified-email"],
    ),
    ("empty enrichment dict", {"contact_enrichment": {}}, ["provider-record"]),
    ("enrichment None", {"contact_enrichment": None}, ["provider-record"]),
    ("no charge for absent value", {}, ["provider-record"]),
]


def test_events_for_record():
    for name, record, expected in CASES:
        got = events_for_record(record)
        assert got == expected, f"{name}: expected {expected}, got {got}"


if __name__ == "__main__":
    failures = 0
    for name, record, expected in CASES:
        got = events_for_record(record)
        status = "OK" if got == expected else "FAIL"
        if got != expected:
            failures += 1
        print(f"[{status}] {name}: {got}")
    print("ALL PASS" if failures == 0 else f"{failures} FAILED")
    sys.exit(1 if failures else 0)
