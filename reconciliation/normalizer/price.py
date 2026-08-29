"""
Deterministic Price Normalizer for LegalMetrix Reconciliation.

Parses and normalizes currency and price representations into comparable numeric float values.
Handles rupee symbols (₹), Rs, Rs., INR, comma separators, and whitespace.
"""

import re
from typing import Any, Optional, Union


def normalize_price(value: Any) -> Optional[float]:
    """
    Normalizes a price representation into a float.

    Examples:
        "₹50" -> 50.0
        "Rs 50" -> 50.0
        "Rs. 50.00" -> 50.0
        "₹ 50" -> 50.0
        "50" -> 50.0
        50 -> 50.0
        "INR 1,250.50" -> 1250.5

    Returns:
        float if successfully parsed, None otherwise.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return round(float(value), 2)

    if not isinstance(value, str):
        value = str(value)

    text = value.strip()
    if not text:
        return None

    # Remove currency tokens and whitespace
    text = re.sub(r'[₹$€£]', '', text)
    text = re.sub(r'\b(rs\.?|inr|mrp|rupees?)\b', '', text, flags=re.IGNORECASE)
    # Remove thousand commas (e.g. 1,250.00 -> 1250.00)
    text = text.replace(',', '')
    text = text.strip()

    # Search for numeric decimal value
    match = re.search(r'[-+]?\d*\.?\d+', text)
    if not match:
        return None

    try:
        val = float(match.group(0))
        return round(val, 2)
    except ValueError:
        return None
