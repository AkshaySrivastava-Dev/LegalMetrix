"""
Unit Tests for LegalMetrix Historical Inspection Comparison.
"""

import pytest
from reconciliation.comparator.historical_comparator import (
    HistoricalStatus,
    compare_historical,
    find_previous_inspections,
    is_same_product,
)


class TestHistoricalComparator:
    # ------------------ Product Identity Matching ------------------ #
    def test_is_same_product_exact_match(self):
        prod1 = {"brand": "Britannia", "product_name": "Good Day", "category": "food", "variant": "100g"}
        prod2 = {"brand": "britannia", "product_name": "good day", "category": "food", "variant": "100g"}
        assert is_same_product(prod1, prod2) is True

    def test_is_same_product_different_name(self):
        prod1 = {"brand": "Britannia", "product_name": "Good Day"}
        prod2 = {"brand": "Britannia", "product_name": "Marie Gold"}
        assert is_same_product(prod1, prod2) is False

    def test_is_same_product_different_brand(self):
        prod1 = {"brand": "BrandA", "product_name": "Biscuits"}
        prod2 = {"brand": "BrandB", "product_name": "Biscuits"}
        assert is_same_product(prod1, prod2) is False

    def test_is_same_product_different_variant(self):
        prod1 = {"product_name": "Demo Soap", "variant": "100g"}
        prod2 = {"product_name": "Demo Soap", "variant": "250g"}
        assert is_same_product(prod1, prod2) is False

    # ------------------ Find Previous Inspections ------------------ #
    def test_find_previous_inspections(self):
        current = {"brand": "Demo", "product_name": "Demo Product", "category": "food", "variant": "500g"}
        inspections = [
            {"inspection_id": "INSP-001", "extracted_data": {"brand": "Demo", "product_name": "Demo Product", "category": "food", "variant": "500g", "mrp": "₹50"}},
            {"inspection_id": "INSP-002", "extracted_data": {"brand": "Other", "product_name": "Other Product", "category": "food"}},
            {"inspection_id": "INSP-003", "extracted_data": {"brand": "demo", "product_name": "demo product", "category": "food", "variant": "500g", "mrp": "₹55"}},
        ]

        matched = find_previous_inspections(current, inspections)
        assert len(matched) == 2
        assert matched[0]["inspection_id"] == "INSP-001"
        assert matched[1]["inspection_id"] == "INSP-003"

    # ------------------ Historical Comparison & Golden Case ------------------ #
    def test_compare_historical_golden_case(self):
        previous = {
            "brand": "Demo",
            "product_name": "Demo Product",
            "category": "food",
            "variant": "500g",
            "mrp": "₹50",
        }
        current = {
            "brand": "Demo",
            "product_name": "Demo Product",
            "category": "food",
            "variant": "500g",
            "mrp": "₹60",
        }

        result = compare_historical(previous, current)

        assert result["status"] == HistoricalStatus.CHANGE_DETECTED.value
        assert result["message"] == "Change detected — officer review recommended."
        assert result["changes_count"] == 1

        change = result["changes"][0]
        assert change["field"] == "mrp"
        assert change["previous"] == "₹50"
        assert change["current"] == "₹60"
        assert change["status"] == "CHANGE_DETECTED"
        assert change["reason"] == "Previous MRP is ₹50.00 vs Current MRP is ₹60.00"

    def test_compare_historical_no_change(self):
        previous = {
            "brand": "Demo",
            "product_name": "Demo Product",
            "mrp": "₹50",
            "net_quantity": "500g",
            "manufacturer": "Demo Foods Ltd",
        }
        current = {
            "brand": "Demo",
            "product_name": "Demo Product",
            "mrp": "Rs 50.00",
            "net_quantity": "500 grams",
            "manufacturer": "demo foods ltd",
        }

        result = compare_historical(previous, current)

        assert result["status"] == HistoricalStatus.NO_CHANGE.value
        assert result["message"] == "No declaration changes detected from previous inspection."
        assert result["changes_count"] == 0
        assert len(result["changes"]) == 0

    def test_compare_historical_multiple_changes(self):
        previous = {
            "product_name": "Demo Shampoo",
            "mrp": "₹150",
            "net_quantity": "200ml",
            "manufacturer": "Old Plant, Gujarat",
        }
        current = {
            "product_name": "Demo Shampoo",
            "mrp": "₹180",
            "net_quantity": "180ml",
            "manufacturer": "New Plant, Baddi",
        }

        result = compare_historical(previous, current)

        assert result["status"] == HistoricalStatus.CHANGE_DETECTED.value
        assert result["changes_count"] == 3
        changed_fields = {c["field"] for c in result["changes"]}
        assert changed_fields == {"mrp", "net_quantity", "manufacturer"}
