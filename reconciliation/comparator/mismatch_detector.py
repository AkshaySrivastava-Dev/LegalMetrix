"""
Mismatch Detector & Product Reconciliation Engine for LegalMetrix.

Performs deterministic reconciliation between physical packaging inspection data
and controlled online catalog/demo data.

Legal Safety Rule:
A mismatch is NOT automatically a legal violation.
It returns 'MISMATCH' with an objective officer review recommendation.
"""

from typing import Any, Dict, List, Optional
from reconciliation.comparator.field_comparator import ComparisonResult, compare_field
from reconciliation.extractor.field_extractor import extract_standard_fields
from reconciliation.extractor.listing_extractor import extract_listing_fields

DEFAULT_FIELDS_TO_COMPARE = [
    "product_name",
    "mrp",
    "net_quantity",
    "manufacturer",
    "country_of_origin",
    "brand",
    "consumer_care",
]


def compare_product(
    physical_data: Optional[Dict[str, Any]],
    online_data: Optional[Dict[str, Any]],
    fields_to_compare: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compares physical commodity declarations against online demo catalog listing.

    Args:
        physical_data: Dict with extracted physical package declarations.
        online_data: Dict with mock/demo online catalog data.
        fields_to_compare: Optional list of fields to reconcile.

    Returns:
        Dict containing:
            - overall: "MATCH" | "MISMATCH" | "UNAVAILABLE"
            - message: Objective explainable summary
            - fields: Dict mapping field names to comparison results
            - matches_count: int
            - mismatches_count: int
            - unavailable_count: int
    """
    phys_extracted = extract_standard_fields(physical_data or {})
    onl_extracted = extract_listing_fields(online_data or {})

    # Combine all target comparison fields
    compare_keys = list(fields_to_compare or DEFAULT_FIELDS_TO_COMPARE)
    # Also include any keys present in either physical or online
    all_keys = set(compare_keys).union(phys_extracted.keys()).union(onl_extracted.keys())
    
    # Maintain consistent ordering with standard fields first
    ordered_keys = [k for k in compare_keys if k in all_keys] + [k for k in sorted(all_keys) if k not in compare_keys]

    field_results: Dict[str, Dict[str, Any]] = {}
    matches_count = 0
    mismatches_count = 0
    unavailable_count = 0

    for key in ordered_keys:
        p_val = phys_extracted.get(key)
        o_val = onl_extracted.get(key)

        # If field is completely absent from both, skip unless it was an explicitly requested key
        if p_val is None and o_val is None and key not in (physical_data or {}) and key not in (online_data or {}):
            continue

        comp = compare_field(key, p_val, o_val)
        field_results[key] = {
            "physical": comp["physical"],
            "online": comp["online"],
            "result": comp["result"],
            "reason": comp.get("reason", ""),
        }

        if comp["result"] == ComparisonResult.MATCH.value:
            matches_count += 1
        elif comp["result"] == ComparisonResult.MISMATCH.value:
            mismatches_count += 1
        else:
            unavailable_count += 1

    # Determine overall status and safe message
    if mismatches_count > 0:
        overall = ComparisonResult.MISMATCH.value
        message = "Potential mismatch detected — officer review recommended."
    elif matches_count > 0:
        overall = ComparisonResult.MATCH.value
        message = "Physical package declarations match online catalog declarations."
    else:
        overall = ComparisonResult.UNAVAILABLE.value
        message = "Insufficient data available to reconcile physical against online declarations."

    return {
        "overall": overall,
        "message": message,
        "fields": field_results,
        "matches_count": matches_count,
        "mismatches_count": mismatches_count,
        "unavailable_count": unavailable_count,
    }
