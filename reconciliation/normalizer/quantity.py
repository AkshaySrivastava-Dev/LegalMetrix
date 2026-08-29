"""
Deterministic Quantity Normalizer for LegalMetrix Reconciliation.

Parses and normalizes net quantity values and measurement units (weight, volume, count)
into comparable standard representations.
"""

import re
from typing import Any, Dict, Optional, Tuple

# Mapping of common unit spellings/abbreviations to standard base unit and multiplier
UNIT_CONVERSION_MAP = {
    # Mass/Weight -> base: 'g'
    "g": ("g", 1.0),
    "gm": ("g", 1.0),
    "gms": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kgs": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
    "kilograms": ("g", 1000.0),
    "mg": ("g", 0.001),
    "milligram": ("g", 0.001),
    "milligrams": ("g", 0.001),
    
    # Volume -> base: 'ml'
    "ml": ("ml", 1.0),
    "m.l.": ("ml", 1.0),
    "millilitre": ("ml", 1.0),
    "millilitres": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "milliliters": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "ltr": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
    "liters": ("ml", 1000.0),
    "litre": ("ml", 1000.0),
    "litres": ("ml", 1000.0),
    
    # Count / Units -> base: 'unit'
    "u": ("unit", 1.0),
    "unit": ("unit", 1.0),
    "units": ("unit", 1.0),
    "n": ("unit", 1.0),
    "no": ("unit", 1.0),
    "nos": ("unit", 1.0),
    "pc": ("unit", 1.0),
    "pcs": ("unit", 1.0),
    "piece": ("unit", 1.0),
    "pieces": ("unit", 1.0),
    "pack": ("unit", 1.0),
    "packet": ("unit", 1.0),
    "count": ("unit", 1.0),
}


def normalize_quantity(value: Any) -> Optional[Dict[str, Any]]:
    """
    Normalizes a net quantity string or dict into a standard comparable structure.

    Examples:
        "500g" -> {"value": 500.0, "unit": "g", "base_value": 500.0, "base_unit": "g"}
        "500 g" -> {"value": 500.0, "unit": "g", "base_value": 500.0, "base_unit": "g"}
        "500 grams" -> {"value": 500.0, "unit": "grams", "base_value": 500.0, "base_unit": "g"}
        "1 kg" -> {"value": 1.0, "unit": "kg", "base_value": 1000.0, "base_unit": "g"}
        "1.5 L" -> {"value": 1.5, "unit": "l", "base_value": 1500.0, "base_unit": "ml"}

    Returns:
        Dict with original value, unit, base_value, base_unit, or None if unparseable.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return {
            "value": float(value),
            "unit": "",
            "base_value": float(value),
            "base_unit": "",
            "formatted": str(value),
        }

    if not isinstance(value, str):
        value = str(value)

    text = value.strip().lower()
    if not text:
        return None

    # Remove net wt / net qty prefixes
    text = re.sub(r'\b(net\s*(wt\.?|weight|qty\.?|quantity|content|vol\.?|volume)?)\b', '', text).strip()
    # Remove colons or equals
    text = re.sub(r'[:=]', '', text).strip()

    # Match numeric portion and following unit string
    match = re.match(r'^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z\.\s]*)$', text)
    if not match:
        # Check if number appears anywhere
        sub_match = re.search(r'([0-9]*\.?[0-9]+)\s*([a-zA-Z\.]+)', text)
        if sub_match:
            match = sub_match
        else:
            return None

    num_str, unit_str = match.groups()
    try:
        val = float(num_str)
    except ValueError:
        return None

    clean_unit = unit_str.strip().rstrip('.')
    
    if clean_unit in UNIT_CONVERSION_MAP:
        base_unit, multiplier = UNIT_CONVERSION_MAP[clean_unit]
        base_val = round(val * multiplier, 4)
    else:
        # Unknown unit, preserve as-is without standard base conversion
        base_unit = clean_unit
        base_val = round(val, 4)

    return {
        "value": val,
        "unit": clean_unit,
        "base_value": base_val,
        "base_unit": base_unit,
        "formatted": f"{val:g} {clean_unit}".strip(),
    }


def compare_quantities(qty1: Any, qty2: Any) -> Optional[bool]:
    """
    Compares two quantities using their base unit representations.
    Returns:
        True if equal, False if unequal, None if unparseable.
    """
    norm1 = normalize_quantity(qty1)
    norm2 = normalize_quantity(qty2)

    if norm1 is None or norm2 is None:
        return None

    # If base units match and are known
    if norm1["base_unit"] and norm2["base_unit"]:
        if norm1["base_unit"] == norm2["base_unit"]:
            return abs(norm1["base_value"] - norm2["base_value"]) < 1e-4
        else:
            # Different unit types (e.g. g vs ml)
            return False

    # Unitless numeric comparison
    return abs(norm1["value"] - norm2["value"]) < 1e-4
