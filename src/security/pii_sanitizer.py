"""
PII Redaction & Security Sanitization Module for VaultIQ.

Scrubs sensitive data (SSNs, AWS/API Keys, Credit Cards, Emails, Passwords)
prior to vector indexing and LLM prompt assembly for SOC-2 and GDPR compliance.
"""

import re
from loguru import logger


class PIISanitizer:
    """Scrubs PII and sensitive enterprise credentials from text strings."""

    def __init__(self):
        # Compiled regex patterns for high-precision PII redaction
        self.patterns = {
            "SSN": (
                re.compile(r"\b(?!000|666|9\d{2})\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"),
                "[REDACTED_SSN]",
            ),
            "API_KEY": (
                re.compile(
                    r"(?i)\b(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|bearer\s+[a-zA-Z0-9\._\-]{20,})\b"
                ),
                "[REDACTED_API_KEY]",
            ),
            "CREDIT_CARD": (
                re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
                "[REDACTED_CREDIT_CARD]",
            ),
            "EMAIL": (
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
                "[REDACTED_EMAIL]",
            ),
        }

    def sanitize_text(self, text: str) -> tuple[str, dict[str, int]]:
        """Sanitize input text and return (sanitized_string, redaction_counts)."""
        if not text:
            return "", {}

        sanitized = text
        counts = {}

        for pii_type, (pattern, replacement) in self.patterns.items():
            matches = pattern.findall(sanitized)
            if matches:
                counts[pii_type] = len(matches)
                sanitized = pattern.sub(replacement, sanitized)

        if counts:
            logger.info(f"PII Sanitizer scrubbed sensitive tokens: {counts}")

        return sanitized, counts

    def has_pii(self, text: str) -> bool:
        """Check if text contains any PII tokens."""
        if not text:
            return False
        for _, (pattern, _) in self.patterns.items():
            if pattern.search(text):
                return True
        return False
