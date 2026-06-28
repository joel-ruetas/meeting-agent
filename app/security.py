"""Security helpers for transcript sanitization and guardrail checks.

This module redacts common PII patterns from text and detects likely
prompt-injection phrases before model execution.
"""

# Imported by CLI and web entry points to enforce pre-model safety checks.

import re

# Phone pattern: requires separators between digit groups
# to avoid matching plain 10-digit numbers like pi digits
PII_PATTERNS = [
    # Email addresses
    (r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
     '[EMAIL_REDACTED]'),
    # US phone numbers — MUST have separators (-, space, parens)
    # Matches: 555-867-5309  (555) 867-5309  +1 555-867-5309
    # Does NOT match: 5558675309 (no separators)
    (r'(\+1[\s\-]?)?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}',
     '[PHONE_REDACTED]'),
    # Social security numbers
    (r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
     '[SSN_REDACTED]'),
]


def scrub_pii(text: str) -> tuple:
    """
    Removes PII from text.
    Returns (cleaned_text, list_of_redacted_descriptions).
    """
    redacted_items = []
    cleaned = text

    for pattern, replacement in PII_PATTERNS:
        matches = re.findall(pattern, cleaned)
        if matches:
            redacted_items.append(
                f"{len(matches)} item(s) matched {replacement}"
            )
            cleaned = re.sub(pattern, replacement, cleaned)

    return cleaned, redacted_items


def check_prompt_injection(text: str) -> bool:
    """
    Returns True if the text contains suspicious instructions
    trying to hijack the agent.
    Normalizes whitespace before checking so double spaces
    do not bypass detection.
    """
    # Normalize: collapse multiple spaces/tabs/newlines to single space
    normalized = re.sub(r'\s+', ' ', text.lower().strip())

    injection_phrases = [
        "ignore previous instructions",
        "forget your instructions",
        "bypass all rules",
        "you are now",
        "act as a different",
        "disregard your",
        "ignore all previous",
        "disregard previous",
        "override your instructions",
    ]

    return any(phrase in normalized for phrase in injection_phrases)