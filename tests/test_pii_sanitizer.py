"""
Unit tests for PII Sanitizer and Security module.
"""

import pytest
from src.security import PIISanitizer


def test_pii_sanitizer_ssn_and_keys():
    sanitizer = PIISanitizer()
    raw_text = "User SSN is 123-45-6789 and AWS key is AKIAIOSFODNN7EXAMPLE."
    clean_text, counts = sanitizer.sanitize_text(raw_text)

    assert "[REDACTED_SSN]" in clean_text
    assert "123-45-6789" not in clean_text
    assert "[REDACTED_API_KEY]" in clean_text
    assert "AKIAIOSFODNN7EXAMPLE" not in clean_text
    assert counts.get("SSN") == 1
    assert counts.get("API_KEY") == 1


def test_pii_sanitizer_email_and_credit_card():
    sanitizer = PIISanitizer()
    raw_text = "Contact admin@bigcorp.com with card 4532-1234-5678-9012."
    clean_text, counts = sanitizer.sanitize_text(raw_text)

    assert "[REDACTED_EMAIL]" in clean_text
    assert "admin@bigcorp.com" not in clean_text
    assert "[REDACTED_CREDIT_CARD]" in clean_text
    assert counts.get("EMAIL") == 1
    assert counts.get("CREDIT_CARD") == 1


def test_has_pii():
    sanitizer = PIISanitizer()
    assert sanitizer.has_pii("Contact test@example.com") is True
    assert sanitizer.has_pii("Regular public documentation text.") is False
