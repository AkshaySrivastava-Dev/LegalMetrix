"""
Online Listing Extractor for Controlled Demo / E-commerce Catalog Data.

Extracts comparable product fields from mock online listing payloads.
NOTE: Works exclusively on controlled demo / static reference data. No web scraping.
"""

from typing import Any, Dict, Optional
from reconciliation.extractor.field_extractor import extract_standard_fields


def extract_listing_fields(listing_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts standardized fields from an online catalog / listing entry.
    Handles nested attributes such as 'pricing', 'specs', or 'details'.
    """
    if not listing_payload or not isinstance(listing_payload, dict):
        return {}

    flattened: Dict[str, Any] = {}

    # Copy top-level keys
    for k, v in listing_payload.items():
        if not isinstance(v, dict):
            flattened[k] = v

    # Check common nested dictionary containers in ecomm mocks
    for container_key in ["specs", "specifications", "pricing", "details", "attributes", "declaration"]:
        container = listing_payload.get(container_key)
        if isinstance(container, dict):
            for k, v in container.items():
                if k not in flattened and not isinstance(v, dict):
                    flattened[k] = v

    return extract_standard_fields(flattened)
