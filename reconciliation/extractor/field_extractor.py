"""
Field Extractor for Physical Commodity Declarations.

Extracts and standardizes field keys from physical inspection payloads.
"""

from typing import Any, Dict, Optional

# Standard field aliases across inspection payloads
FIELD_ALIASES = {
    "product_name": ["product_name", "product", "item_name", "title", "commodity_name"],
    "brand": ["brand", "brand_name", "make"],
    "mrp": ["mrp", "price", "retail_price", "maximum_retail_price"],
    "net_quantity": ["net_quantity", "quantity", "net_qty", "net_weight", "net_vol", "net_content"],
    "manufacturer": ["manufacturer", "packer", "manufacturer_details", "mfg_by", "packed_by", "importer"],
    "country_of_origin": ["country_of_origin", "origin_country", "country", "made_in"],
    "category": ["category", "product_category", "type"],
    "variant": ["variant", "flavor", "pack_size", "version"],
    "date_of_manufacture": ["date_of_manufacture", "mfg_date", "date_of_packaging", "pkg_date"],
    "consumer_care": ["consumer_care", "customer_care", "helpline", "consumer_cell"],
}


def extract_standard_fields(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts a standardized key-value dictionary from an input payload.
    Resolves common aliases to canonical keys.
    """
    if not payload or not isinstance(payload, dict):
        return {}

    result = {}
    # First, populate directly known keys
    for canonical, aliases in FIELD_ALIASES.items():
        val = None
        for alias in aliases:
            if alias in payload and payload[alias] is not None:
                val = payload[alias]
                break
        if val is not None:
            result[canonical] = val

    # Include any extra keys from payload that don't collide
    for k, v in payload.items():
        if k not in result and not any(k in aliases for aliases in FIELD_ALIASES.values()):
            result[k] = v

    return result
