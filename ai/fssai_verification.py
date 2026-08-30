"""
Centralized FSSAI Status & Verification Engine.

Evaluates FSSAI food business operator registration/license status for packaged commodities.

Taxonomy:
- VERIFIED: Verified against FoSCoS/FSSAI reference master data
- DEMO_VERIFIED: Configured demo verification data
- NOT_VERIFIED: Food-related product but license details are missing or unverified
- NOT_APPLICABLE: Non-food category (household, electronics, personal care)
- PENDING_VERIFICATION: Detected from OCR but awaiting external reference match
"""

import re
from typing import Dict, Any, Optional

FOOD_CATEGORIES = {
    "food", "beverage", "snack", "dairy", "packaged_food", "confectionery", "bakery", "oil"
}

FSSAI_REFERENCE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "pepsi": {
        "status": "DEMO_VERIFIED",
        "license_number": "10014064000435",
        "source": "demo_reference",
        "message": "FSSAI status from configured demo reference data."
    },
    "maaza": {
        "status": "DEMO_VERIFIED",
        "license_number": "10012011000620",
        "source": "demo_reference",
        "message": "FSSAI status from configured demo reference data."
    },
    "too_yumm": {
        "status": "DEMO_VERIFIED",
        "license_number": "10017031002079",
        "source": "demo_reference",
        "message": "FSSAI status from configured demo reference data."
    },
    "badam_milk": {
        "status": "DEMO_VERIFIED",
        "license_number": "10014047000258",
        "source": "demo_reference",
        "message": "FSSAI status from configured demo reference data."
    }
}


def _normalize_text(text: str) -> str:
    """Normalize text for consistent brand/product matching."""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def evaluate_fssai_status(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    product_name: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates the FSSAI verification status for a packaged commodity.

    Args:
        category: Product category (e.g. food, beverage, personal_care, household)
        brand: Detected brand name
        product_name: Detected product name
        fields: Full dictionary of extracted fields

    Returns:
        Dict with keys:
            - status: "VERIFIED" | "DEMO_VERIFIED" | "NOT_VERIFIED" | "NOT_APPLICABLE" | "PENDING_VERIFICATION"
            - license_number: Optional 14-digit FSSAI license number string
            - source: "demo_reference" | "fssai_reference" | "package_ocr" | None
            - message: Descriptive status message
    """
    fields = fields or {}
    category_str = (category or "").lower().strip()

    # If category is personal_care or household or clearly non-food -> NOT_APPLICABLE
    if category_str in ["personal_care", "household", "electronics", "apparel", "hardware"]:
        return {
            "status": "NOT_APPLICABLE",
            "license_number": None,
            "source": None,
            "message": "FSSAI food registration is not applicable to this product category."
        }

    # Extract any OCR-detected FSSAI license number from fields
    ocr_license = None
    if "fssai_license_number" in fields:
        val = fields.get("fssai_license_number")
        if isinstance(val, dict):
            ocr_license = val.get("value")
        elif isinstance(val, str):
            ocr_license = val

    # Build normalized candidate text for brand matching
    candidates = []
    if brand:
        candidates.append(str(brand))
    if product_name:
        candidates.append(str(product_name))
    for k in ["brand", "product_name"]:
        val = fields.get(k)
        if isinstance(val, dict):
            v = val.get("value")
            if v and str(v) not in candidates:
                candidates.append(str(v))
        elif isinstance(val, str) and val not in candidates:
            candidates.append(val)

    combined_text = _normalize_text(" ".join(candidates))

    # 1. Match Pepsi
    if any(tok in combined_text for tok in ["pepsi", "pepsl", "peps1", "pepci"]):
        ref = FSSAI_REFERENCE_REGISTRY["pepsi"]
        return {
            "status": ref["status"],
            "license_number": ref["license_number"],
            "source": ref["source"],
            "message": ref["message"]
        }

    # 2. Match Maaza
    if any(tok in combined_text for tok in ["maaza", "mazza", "maza", "merea"]):
        ref = FSSAI_REFERENCE_REGISTRY["maaza"]
        return {
            "status": ref["status"],
            "license_number": ref["license_number"],
            "source": ref["source"],
            "message": ref["message"]
        }

    # 3. Match Too Yumm
    if any(tok in combined_text for tok in ["too yumm", "tooyumm", "asc chips", "american style"]):
        ref = FSSAI_REFERENCE_REGISTRY["too_yumm"]
        return {
            "status": ref["status"],
            "license_number": ref["license_number"],
            "source": ref["source"],
            "message": ref["message"]
        }

    # 4. Match Badam Milk
    if any(tok in combined_text for tok in ["badam milk", "badamm", "badamml", "jersey badam"]):
        ref = FSSAI_REFERENCE_REGISTRY["badam_milk"]
        return {
            "status": ref["status"],
            "license_number": ref["license_number"],
            "source": ref["source"],
            "message": ref["message"]
        }

    # 5. Food item without verified reference match
    if category_str in FOOD_CATEGORIES or not category_str or category_str == "unknown":
        if ocr_license:
            return {
                "status": "NOT_VERIFIED",
                "license_number": str(ocr_license),
                "source": "package_ocr",
                "message": "FSSAI license details detected from packaging OCR but not verified against reference database."
            }
        return {
            "status": "NOT_VERIFIED",
            "license_number": None,
            "source": None,
            "message": "FSSAI license details could not be verified from available evidence."
        }

    # Default fallback
    return {
        "status": "NOT_APPLICABLE",
        "license_number": None,
        "source": None,
        "message": "FSSAI food registration is not applicable to this product category."
    }
