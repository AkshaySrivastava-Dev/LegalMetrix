"""
Field Comparator for LegalMetrix Reconciliation.

Compares individual fields between physical packaging and online listing data
using deterministic normalizers.
"""

from enum import Enum
from typing import Any, Dict, Optional

from reconciliation.normalizer.price import normalize_price
from reconciliation.normalizer.quantity import compare_quantities, normalize_quantity
from reconciliation.normalizer.text import are_texts_equivalent, normalize_text


class ComparisonResult(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNAVAILABLE = "UNAVAILABLE"


def compare_field(field_name: str, physical_val: Any, online_val: Any) -> Dict[str, Any]:
    """
    Compares a single field between physical extraction and online data.

    Returns:
        Dict with keys:
            - physical: original physical value
            - online: original online value
            - result: "MATCH" | "MISMATCH" | "UNAVAILABLE"
            - reason: explanatory string
    """
    # 1. Check availability
    phys_empty = physical_val is None or (isinstance(physical_val, str) and not physical_val.strip())
    onl_empty = online_val is None or (isinstance(online_val, str) and not online_val.strip())

    if phys_empty and onl_empty:
        return {
            "physical": physical_val,
            "online": online_val,
            "result": ComparisonResult.UNAVAILABLE.value,
            "reason": "Field is unavailable in both physical and online records",
        }

    if phys_empty:
        return {
            "physical": physical_val,
            "online": online_val,
            "result": ComparisonResult.UNAVAILABLE.value,
            "reason": "Physical declaration is unavailable for comparison",
        }

    if onl_empty:
        return {
            "physical": physical_val,
            "online": online_val,
            "result": ComparisonResult.UNAVAILABLE.value,
            "reason": "Online catalog declaration is unavailable for comparison",
        }

    norm_field = field_name.lower().strip()

    # 2. Price / MRP comparison
    if norm_field in ["mrp", "price", "retail_price"]:
        norm_p = normalize_price(physical_val)
        norm_o = normalize_price(online_val)

        if norm_p is None or norm_o is None:
            # Fallback to direct string check if normalization fails
            if str(physical_val).strip() == str(online_val).strip():
                return {
                    "physical": physical_val,
                    "online": online_val,
                    "result": ComparisonResult.MATCH.value,
                    "reason": "Exact price string match",
                }
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MISMATCH.value,
                "reason": f"Price values '{physical_val}' and '{online_val}' could not be parsed identically",
            }

        if abs(norm_p - norm_o) < 0.01:
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MATCH.value,
                "reason": f"Normalized prices match (₹{norm_p:.2f})",
            }
        else:
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MISMATCH.value,
                "reason": f"Price difference detected: Physical is ₹{norm_p:.2f} vs Online is ₹{norm_o:.2f}",
            }

    # 3. Net Quantity comparison
    if norm_field in ["net_quantity", "quantity", "net_qty", "net_weight", "net_vol"]:
        qty_match = compare_quantities(physical_val, online_val)
        if qty_match is True:
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MATCH.value,
                "reason": "Normalized net quantities match standard unit representation",
            }
        elif qty_match is False:
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MISMATCH.value,
                "reason": f"Quantity mismatch: Physical '{physical_val}' vs Online '{online_val}'",
            }
        else:
            # Fallback to text equivalence
            if are_texts_equivalent(physical_val, online_val):
                return {
                    "physical": physical_val,
                    "online": online_val,
                    "result": ComparisonResult.MATCH.value,
                    "reason": "Quantity text equivalent after normalization",
                }
            return {
                "physical": physical_val,
                "online": online_val,
                "result": ComparisonResult.MISMATCH.value,
                "reason": f"Quantity values differ: '{physical_val}' vs '{online_val}'",
            }

    # 4. Standard text comparison (Product name, manufacturer, country of origin, etc.)
    if are_texts_equivalent(physical_val, online_val):
        return {
            "physical": physical_val,
            "online": online_val,
            "result": ComparisonResult.MATCH.value,
            "reason": "Normalized declaration texts match",
        }
    else:
        return {
            "physical": physical_val,
            "online": online_val,
            "result": ComparisonResult.MISMATCH.value,
            "reason": f"Declaration text differs: Physical is '{physical_val}' vs Online is '{online_val}'",
        }
