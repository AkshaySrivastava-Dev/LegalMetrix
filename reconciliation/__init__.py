"""
Reconciliation and Comparison Module for LegalMetrix.
"""

from reconciliation.comparator import (
    ComparisonResult,
    HistoricalStatus,
    compare_field,
    compare_historical,
    compare_product,
    find_previous_inspections,
    is_same_product,
)
from reconciliation.extractor import (
    extract_listing_fields,
    extract_standard_fields,
)
from reconciliation.normalizer import (
    are_texts_equivalent,
    compare_quantities,
    normalize_price,
    normalize_quantity,
    normalize_text,
)

__all__ = [
    "compare_product",
    "compare_historical",
    "find_previous_inspections",
    "is_same_product",
    "compare_field",
    "ComparisonResult",
    "HistoricalStatus",
    "normalize_price",
    "normalize_quantity",
    "compare_quantities",
    "normalize_text",
    "are_texts_equivalent",
    "extract_standard_fields",
    "extract_listing_fields",
]
