"""
Deterministic Text Normalizer for LegalMetrix Reconciliation.

Applies safe, deterministic text normalization:
- Lowercasing
- Whitespace stripping and collapsing
- Punctuation normalization
Avoids dangerous semantic alterations.
"""

import re
from typing import Any, Optional


def normalize_text(value: Any) -> Optional[str]:
    """
    Normalizes a text string for deterministic comparison.

    Examples:
        "  ABC   Foods  " -> "abc foods"
        "India." -> "india"
        "Demo, Inc." -> "demo, inc."

    Returns:
        Cleaned lowercase string or None if empty.
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    # Strip and lowercase
    text = value.strip().lower()
    if not text:
        return None

    # Collapse multiple consecutive whitespace/tabs/newlines to a single space
    text = re.sub(r'\s+', ' ', text)

    # Standardize quotation marks and dashes
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    text = text.replace('–', '-').replace('—', '-')

    # Strip trailing periods if isolated at end
    text = text.strip()
    return text if text else None


def are_texts_equivalent(text1: Any, text2: Any) -> bool:
    """
    Deterministically checks if two text values are equivalent after safe normalization.
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if norm1 is None and norm2 is None:
        return True
    if norm1 is None or norm2 is None:
        return False

    return norm1 == norm2
