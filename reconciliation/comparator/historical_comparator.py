"""
Historical Inspection Comparator for LegalMetrix.

Identifies same-product previous inspections and detects changes across declarations over time.

Legal Safety Rule:
A historical change is NOT automatically illegal.
Returns 'CHANGE_DETECTED' with an objective officer review recommendation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from reconciliation.comparator.field_comparator import ComparisonResult, compare_field
from reconciliation.extractor.field_extractor import extract_standard_fields
from reconciliation.normalizer.price import normalize_price
from reconciliation.normalizer.text import are_texts_equivalent, normalize_text


class HistoricalStatus(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    CHANGE_DETECTED = "CHANGE_DETECTED"
    UNAVAILABLE = "UNAVAILABLE"


def is_same_product(prod_a: Dict[str, Any], prod_b: Dict[str, Any]) -> bool:
    """
    Determines if two product payloads correspond to the same product identity.
    Uses: brand, product_name, category, variant.
    """
    fields_a = extract_standard_fields(prod_a)
    fields_b = extract_standard_fields(prod_b)

    # Product name is mandatory for identity
    name_a = fields_a.get("product_name")
    name_b = fields_b.get("product_name")
    if not name_a or not name_b:
        return False
    if not are_texts_equivalent(name_a, name_b):
        return False

    # Check brand if provided in either
    brand_a = fields_a.get("brand")
    brand_b = fields_b.get("brand")
    if brand_a and brand_b and not are_texts_equivalent(brand_a, brand_b):
        return False

    # Check category if provided in either
    cat_a = fields_a.get("category")
    cat_b = fields_b.get("category")
    if cat_a and cat_b and not are_texts_equivalent(cat_a, cat_b):
        return False

    # Check variant if provided in either
    var_a = fields_a.get("variant")
    var_b = fields_b.get("variant")
    if var_a and var_b and not are_texts_equivalent(var_a, var_b):
        return False

    return True


def find_previous_inspections(
    current_product: Dict[str, Any],
    previous_inspections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Filters a list of historical inspections to find records corresponding to the same product.

    Args:
        current_product: Current inspection or product dict.
        previous_inspections: List of previous inspection dictionaries.

    Returns:
        List of matching previous inspection records.
    """
    if not previous_inspections:
        return []

    matched = []
    for insp in previous_inspections:
        # Check either 'extracted_data' or the inspection dict directly
        target_dict = insp.get("extracted_data", insp)
        if is_same_product(current_product, target_dict):
            matched.append(insp)

    return matched


def compare_historical(
    previous_data: Optional[Dict[str, Any]],
    current_data: Optional[Dict[str, Any]],
    fields_to_track: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compares declarations between a previous inspection and current inspection of the same product.

    Args:
        previous_data: Historical inspection data.
        current_data: Current inspection data.
        fields_to_track: Optional list of fields to compare.

    Returns:
        Dict containing:
            - status: "CHANGE_DETECTED" | "NO_CHANGE" | "UNAVAILABLE"
            - message: Objective summary recommendation
            - changes: List of modified fields
            - compared_fields: Dict of full field comparisons
    """
    if not previous_data and not current_data:
        return {
            "status": HistoricalStatus.UNAVAILABLE.value,
            "message": "Both previous and current inspection data are unavailable.",
            "changes": [],
            "compared_fields": {},
        }

    prev_extracted = extract_standard_fields(previous_data or {})
    curr_extracted = extract_standard_fields(current_data or {})

    track_keys = fields_to_track or [
        "mrp",
        "net_quantity",
        "manufacturer",
        "country_of_origin",
        "date_of_manufacture",
        "consumer_care",
    ]

    all_keys = set(track_keys).union(prev_extracted.keys()).union(curr_extracted.keys())
    ordered_keys = [k for k in track_keys if k in all_keys] + [k for k in sorted(all_keys) if k not in track_keys]

    changes: List[Dict[str, Any]] = []
    compared_fields: Dict[str, Any] = {}

    for key in ordered_keys:
        p_val = prev_extracted.get(key)
        c_val = curr_extracted.get(key)

        if p_val is None and c_val is None:
            continue

        comp = compare_field(key, p_val, c_val)
        result_status = comp["result"]

        norm_key = key.lower().strip()
        if norm_key in ["mrp", "price", "retail_price"]:
            norm_p = normalize_price(p_val)
            norm_c = normalize_price(c_val)
            if norm_p is not None and norm_c is not None:
                if abs(norm_p - norm_c) < 0.01:
                    hist_reason = f"Previous and Current MRP match (₹{norm_p:.2f})"
                else:
                    hist_reason = f"Previous MRP is ₹{norm_p:.2f} vs Current MRP is ₹{norm_c:.2f}"
            else:
                hist_reason = f"Previous MRP '{p_val}' vs Current MRP '{c_val}'"
        elif norm_key in ["net_quantity", "quantity", "net_qty", "net_weight", "net_vol"]:
            if result_status == ComparisonResult.MATCH.value:
                hist_reason = "Net quantity unchanged between inspections"
            else:
                hist_reason = f"Previous quantity '{p_val}' vs Current quantity '{c_val}'"
        else:
            if result_status == ComparisonResult.MATCH.value:
                hist_reason = f"Declaration '{key}' unchanged"
            else:
                hist_reason = f"Previous declaration '{p_val}' vs Current declaration '{c_val}'"

        compared_fields[key] = {
            "previous": p_val,
            "current": c_val,
            "result": result_status,
            "reason": hist_reason,
        }

        # In historical context, MISMATCH means a declaration changed between inspections
        if result_status == ComparisonResult.MISMATCH.value:
            changes.append({
                "field": key,
                "previous": p_val,
                "current": c_val,
                "status": "CHANGE_DETECTED",
                "reason": hist_reason,
            })

    if changes:
        status = HistoricalStatus.CHANGE_DETECTED.value
        message = "Change detected — officer review recommended."
    else:
        status = HistoricalStatus.NO_CHANGE.value
        message = "No declaration changes detected from previous inspection."

    return {
        "status": status,
        "message": message,
        "changes_count": len(changes),
        "changes": changes,
        "compared_fields": compared_fields,
    }
