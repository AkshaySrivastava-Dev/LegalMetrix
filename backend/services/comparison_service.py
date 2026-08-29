"""
Comparison Service.
Integrates Physical Inspection Data with Controlled Online Demo Catalog data.
Allows Legal Metrology Officers to verify whether on-shelf pack declarations match
registered / listed e-commerce catalogue declarations (MRP, Net Qty, Manufacturer, etc.).
NOTE: Does NOT scrape external sites; uses controlled reference demo data.
"""

import logging
from typing import Dict, Any, Optional, List
from ..models.schemas import ComparisonResponse, FieldComparison, ComparisonRequest

logger = logging.getLogger("legal_metrology.comparison_service")

# Controlled reference dataset representing verified standard online listings
CONTROLLED_ONLINE_CATALOG = [
    {
        "product_name": "Krunchy Treat Butter Cookies",
        "brand": "Britannica Foods",
        "category": "packaged_food",
        "variant": "Butter Delite 150g",
        "mrp": "₹45.00",
        "net_quantity": "150 g",
        "manufacturer": "Britannica Industries Ltd., Plot 12, Industrial Area, Sector 62, Noida - 201301, UP, India",
    },
    {
        "product_name": "Pure Gold Refined Mustard Oil",
        "brand": "Dhara Agro",
        "category": "edible_oil",
        "variant": "Pouch 1L",
        "mrp": "₹160.00",  # Slight intentional difference to demo MRP mismatch detection
        "net_quantity": "1 L / 910 g",
        "manufacturer": "Dhara Agro Processing Pvt Ltd, Phase II, RIICO, Jaipur - 302022, Rajasthan, India",
    },
    {
        "product_name": "Sparkle Active Detergent Powder",
        "brand": "CleanMaster",
        "category": "household_cleaning",
        "variant": "Lemon Fresh 1kg",
        "mrp": "₹120.00",
        "net_quantity": "1 kg",
        "manufacturer": "CleanMaster Homecare Corp, GIDC Estate, Vatva, Ahmedabad - 382445, Gujarat",
    },
    {
        "product_name": "Parle-G Gold Glucose Biscuits",
        "brand": "Parle",
        "category": "packaged_food",
        "variant": "100g Pack",
        "mrp": "₹10.00",
        "net_quantity": "100 g",
        "manufacturer": "Parle Products Pvt Ltd, Vile Parle East, Mumbai 400057",
    },
]


def _normalize_string(val: Optional[str]) -> str:
    """Helper to clean string for comparison."""
    if not val:
        return ""
    import re
    # Remove currency symbols and non-alphanumeric noise for soft matching
    cleaned = re.sub(r"[₹,.\(\)\[\]\-]", " ", str(val).lower())
    return " ".join(cleaned.split())


def _find_catalog_entry(brand: Optional[str], product_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Finds best matching catalog entry based on brand and product name."""
    norm_brand = _normalize_string(brand)
    norm_name = _normalize_string(product_name)

    if not norm_brand and not norm_name:
        return None

    # 1. Exact or partial brand + product match
    for item in CONTROLLED_ONLINE_CATALOG:
        cat_brand = _normalize_string(item.get("brand"))
        cat_name = _normalize_string(item.get("product_name"))

        if (cat_brand in norm_brand or norm_brand in cat_brand) and (
            cat_name in norm_name or norm_name in cat_name
        ):
            return item

    # 2. Fallback brand or product match
    for item in CONTROLLED_ONLINE_CATALOG:
        cat_brand = _normalize_string(item.get("brand"))
        cat_name = _normalize_string(item.get("product_name"))

        if (norm_brand and norm_brand in cat_brand) or (norm_name and norm_name in cat_name):
            return item

    return None


def compare_product(
    data: Dict[str, Any]
) -> ComparisonResponse:
    """
    Compares physical inspection data against controlled online catalogue reference.
    Returns field-by-field match details and overall comparison status.
    """
    brand = data.get("brand")
    product_name = data.get("product_name")

    catalog_item = _find_catalog_entry(brand, product_name)

    if not catalog_item:
        return ComparisonResponse(
            status="unavailable",
            product_name=product_name,
            brand=brand,
            matched_fields=[],
            mismatched_fields=[],
            details=[],
            online_source="Controlled Demo Catalog",
            message="No verified online benchmark product found matching the physical product attributes.",
        )

    fields_to_compare = [
        ("brand", "Brand Name"),
        ("product_name", "Product Name"),
        ("mrp", "Maximum Retail Price (MRP)"),
        ("net_quantity", "Net Quantity"),
        ("manufacturer", "Manufacturer / Packer"),
        ("variant", "Product Variant"),
    ]

    matched_fields: List[str] = []
    mismatched_fields: List[str] = []
    details: List[FieldComparison] = []

    for field_key, field_label in fields_to_compare:
        phys_val = data.get(field_key)
        online_val = catalog_item.get(field_key)

        if not phys_val and not online_val:
            continue

        norm_phys = _normalize_string(phys_val)
        norm_online = _normalize_string(online_val)

        # Evaluate match: check if key numbers/words match
        is_match = False
        if norm_phys == norm_online:
            is_match = True
        elif norm_phys and norm_online and (norm_phys in norm_online or norm_online in norm_phys):
            is_match = True
        else:
            # Special check for MRP numbers
            import re
            p_nums = re.findall(r"\d+(?:\.\d+)?", str(phys_val or ""))
            o_nums = re.findall(r"\d+(?:\.\d+)?", str(online_val or ""))
            if p_nums and o_nums and p_nums[0] == o_nums[0]:
                is_match = True

        if is_match:
            matched_fields.append(field_key)
            details.append(
                FieldComparison(
                    field=field_label,
                    physical_value=str(phys_val) if phys_val else None,
                    online_value=str(online_val) if online_val else None,
                    matched=True,
                    note="Values match verified online listing.",
                )
            )
        else:
            mismatched_fields.append(field_key)
            details.append(
                FieldComparison(
                    field=field_label,
                    physical_value=str(phys_val) if phys_val else "Not Detected",
                    online_value=str(online_val) if online_val else "Not Listed",
                    matched=False,
                    note="Discrepancy detected between physical packaging and online benchmark.",
                )
            )

    status = "matched" if not mismatched_fields else "mismatched"
    message = (
        "Physical declarations match online benchmark data."
        if status == "matched"
        else f"Discrepancies identified in {len(mismatched_fields)} field(s) (e.g. {', '.join(mismatched_fields)})."
    )

    return ComparisonResponse(
        status=status,
        product_name=catalog_item.get("product_name"),
        brand=catalog_item.get("brand"),
        matched_fields=matched_fields,
        mismatched_fields=mismatched_fields,
        details=details,
        online_source="Controlled Demo Catalog",
        message=message,
    )
