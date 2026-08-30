"""
Centralized Fraud / Anomaly Detection and Human Review Layer.

Provides deterministic comparison of OCR-extracted declarations against
configured product reference definitions, and evaluates mandatory human review criteria.

Key Capabilities:
1. Reference Mismatch / Potential Fraud Detection:
   - Compares actual extracted fields against expected product reference values (e.g. Badam Milk: 200 ml, JERSEY, India).
   - Generates detailed mismatch records with field name, expected value, actual value, source view, and confidence.
   - Strictly avoids classifying missing/unreadable fields as fraud.
2. Mandatory Human Review Detection:
   - Enforces human inspection if manufacturing_date or expiry_date is missing or has low confidence.
3. Provenance & Non-Definitive Fraud Labelling:
   - Clearly flags as "POTENTIAL_FRAUD" / "Value Mismatch" rather than making definitive claims.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# Centralized Product Reference Definitions
PRODUCT_REFERENCE_RULES: Dict[str, Dict[str, Any]] = {
    "badam_milk": {
        "canonical_name": "Badam Milk",
        "aliases": [
            "badam milk", "badamm", "badamml", "badamm milk",
            "badammilk", "badam mil k", "jersey badam milk", "jersey badam"
        ],
        "expected": {
            "brand": "Badam Milk",
            "net_quantity": "200 ml",
            "manufacturer": "JERSEY",
            "country_of_origin": "India"
        }
    }
}


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_field_value(field_data: Any) -> Tuple[Optional[str], Optional[float], Optional[str], Optional[Any]]:
    """Extracts (value_str, confidence, source_view, box) from field data."""
    if field_data is None:
        return None, None, None, None
    if isinstance(field_data, dict):
        val = field_data.get("value")
        conf = field_data.get("confidence")
        src = field_data.get("source_view") or field_data.get("source")
        box = field_data.get("box")
        unit = field_data.get("unit")
        if val is not None:
            val_str = f"{val} {unit}".strip() if unit else str(val).strip()
            return val_str, conf, src, box
        return None, conf, src, box
    val_str = str(field_data).strip()
    return val_str, None, None, None


def _values_match(expected: str, actual: str, field_name: str) -> bool:
    """Checks whether actual extracted value matches expected reference value."""
    norm_exp = _normalize_text(expected)
    norm_act = _normalize_text(actual)

    if norm_exp == norm_act:
        return True

    # For net quantity: e.g. "200 ml" vs "200ml" or "200"
    if field_name == "net_quantity":
        exp_digits = re.findall(r'\d+', norm_exp)
        act_digits = re.findall(r'\d+', norm_act)
        if exp_digits and act_digits and exp_digits == act_digits:
            return True
        return False

    # For manufacturer: substring or alias matching (e.g. "JERSEY" in "JERSEY PVT LTD")
    if field_name == "manufacturer":
        if norm_exp in norm_act or norm_act in norm_exp:
            return True
        return False

    # For country of origin: e.g. "India" vs "INDIA"
    if field_name == "country_of_origin":
        if norm_exp in norm_act or norm_act in norm_exp:
            return True
        return False

    # For brand:
    if field_name == "brand":
        if norm_exp in norm_act or norm_act in norm_exp:
            return True
        return False

    return False


def determine_review_status(fields: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether mandatory human inspection is required.
    Triggered when:
    - manufacturing_date is missing or has low confidence (< 0.60)
    - expiry_date is missing or has low confidence (< 0.60)
    """
    mfg_val, mfg_conf, _, _ = _extract_field_value(fields.get("manufacturing_date"))
    exp_val, exp_conf, _, _ = _extract_field_value(fields.get("expiry_date"))

    reasons = []
    if not mfg_val:
        reasons.append("Manufacturing date is missing or unreadable")
    elif mfg_conf is not None and mfg_conf < 0.60:
        reasons.append(f"Manufacturing date has low OCR confidence ({round(mfg_conf * 100)}%)")

    if not exp_val:
        reasons.append("Expiry date is missing or unreadable")
    elif exp_conf is not None and exp_conf < 0.60:
        reasons.append(f"Expiry date has low OCR confidence ({round(exp_conf * 100)}%)")

    if reasons:
        return True, " • ".join(reasons)
    return False, None


def evaluate_fraud_and_review(
    fields: Optional[Dict[str, Any]] = None,
    brand: Optional[str] = None,
    product_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates potential fraud / value mismatches and human review requirements.

    Returns:
        Dict with keys:
            - status: "POTENTIAL_FRAUD" | "MANUAL_REVIEW" | "INSUFFICIENT_EVIDENCE" | "NO_MISMATCH" | "NO_REFERENCE"
            - review_required: bool
            - mismatches: List of mismatch objects
            - reason: Optional descriptive reason
    """
    fields = fields or {}

    # Step 1: Check mandatory date human review status
    review_required, review_reason = determine_review_status(fields)

    # Step 2: Identify configured product reference rule
    candidates = []
    if brand:
        candidates.append(str(brand))
    if product_name:
        candidates.append(str(product_name))
    
    brand_field_val, _, _, _ = _extract_field_value(fields.get("brand"))
    if brand_field_val and brand_field_val not in candidates:
        candidates.append(brand_field_val)

    prod_field_val, _, _, _ = _extract_field_value(fields.get("product_name"))
    if prod_field_val and prod_field_val not in candidates:
        candidates.append(prod_field_val)

    combined_text = _normalize_text(" ".join(candidates))

    matched_ref_key = None
    matched_ref_def = None

    for ref_key, ref_def in PRODUCT_REFERENCE_RULES.items():
        for alias in ref_def.get("aliases", []):
            if _normalize_text(alias) in combined_text:
                matched_ref_key = ref_key
                matched_ref_def = ref_def
                break
        if matched_ref_key:
            break

    # If no reference rule applies to this product
    if not matched_ref_def:
        if review_required:
            return {
                "status": "MANUAL_REVIEW",
                "review_required": True,
                "mismatches": [],
                "reason": review_reason or "Manufacturing or expiry date could not be reliably verified."
            }
        return {
            "status": "NO_REFERENCE",
            "review_required": False,
            "mismatches": [],
            "reason": None
        }

    # Step 3: Compare extracted fields against expected values
    expected_dict = matched_ref_def.get("expected", {})
    mismatches: List[Dict[str, Any]] = []
    missing_evidence_count = 0
    total_expected_count = len(expected_dict)

    for field_name, expected_val in expected_dict.items():
        actual_val, actual_conf, actual_src, actual_box = _extract_field_value(fields.get(field_name))

        if actual_val is None:
            # Field was not detected by OCR -> NOT fraud automatically
            missing_evidence_count += 1
            continue

        if not _values_match(expected_val, actual_val, field_name):
            # Confirmed value difference -> POTENTIAL_FRAUD
            mismatch_item = {
                "field": field_name,
                "expected": expected_val,
                "actual": actual_val,
                "source": actual_src or "uploaded_image",
                "confidence": actual_conf,
            }
            if actual_box:
                mismatch_item["box"] = actual_box
            mismatches.append(mismatch_item)

    # Step 4: Determine final status
    if mismatches:
        # One or more actual values conflict with expected values
        mismatched_fields = ", ".join([m["field"] for m in mismatches])
        return {
            "status": "POTENTIAL_FRAUD",
            "review_required": review_required,
            "mismatches": mismatches,
            "reason": f"Value mismatch detected for {mismatched_fields} against configured reference."
        }

    if missing_evidence_count > 0 and missing_evidence_count == total_expected_count:
        # All reference fields were missing from OCR
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "review_required": True,
            "mismatches": [],
            "reason": "Reference fields could not be verified due to missing OCR declarations."
        }

    if review_required:
        # Values that were detected match, but dates are missing/uncertain
        return {
            "status": "MANUAL_REVIEW",
            "review_required": True,
            "mismatches": [],
            "reason": review_reason or "Manufacturing or expiry date could not be reliably verified."
        }

    # All observed fields match expected reference with valid dates
    return {
        "status": "NO_MISMATCH",
        "review_required": False,
        "mismatches": [],
        "reason": "All extracted values match configured product reference."
    }
