"""
Unit Tests for LegalMetrix Price, Quantity, and Text Normalizers.
"""

import pytest
from reconciliation.normalizer.price import normalize_price
from reconciliation.normalizer.quantity import compare_quantities, normalize_quantity
from reconciliation.normalizer.text import are_texts_equivalent, normalize_text


class TestNormalizers:
    # ------------------ Price Normalizer ------------------ #
    def test_normalize_price_formats(self):
        assert normalize_price("₹50") == 50.0
        assert normalize_price("Rs 50") == 50.0
        assert normalize_price("Rs. 50") == 50.0
        assert normalize_price("₹ 50") == 50.0
        assert normalize_price("50") == 50.0
        assert normalize_price(50) == 50.0
        assert normalize_price(50.50) == 50.5
        assert normalize_price("₹ 1,250.75") == 1250.75
        assert normalize_price("INR 99.00 (inclusive of all taxes)") == 99.0

    def test_normalize_price_invalid(self):
        assert normalize_price(None) is None
        assert normalize_price("") is None
        assert normalize_price("   ") is None
        assert normalize_price("Price on request") is None

    # ------------------ Quantity Normalizer ------------------ #
    def test_normalize_quantity_formats(self):
        q1 = normalize_quantity("500g")
        assert q1["value"] == 500.0
        assert q1["base_value"] == 500.0
        assert q1["base_unit"] == "g"

        q2 = normalize_quantity("500 g")
        assert q2["value"] == 500.0
        assert q2["base_value"] == 500.0
        assert q2["base_unit"] == "g"

        q3 = normalize_quantity("500 grams")
        assert q3["value"] == 500.0
        assert q3["base_value"] == 500.0
        assert q3["base_unit"] == "g"

        q4 = normalize_quantity("1 kg")
        assert q4["value"] == 1.0
        assert q4["base_value"] == 1000.0
        assert q4["base_unit"] == "g"

        q5 = normalize_quantity("1.5 L")
        assert q5["value"] == 1.5
        assert q5["base_value"] == 1500.0
        assert q5["base_unit"] == "ml"

        q6 = normalize_quantity("750 ml")
        assert q6["value"] == 750.0
        assert q6["base_value"] == 750.0
        assert q6["base_unit"] == "ml"

        q7 = normalize_quantity("Net Qty: 10 Units")
        assert q7["value"] == 10.0
        assert q7["base_value"] == 10.0
        assert q7["base_unit"] == "unit"

    def test_compare_quantities(self):
        assert compare_quantities("500g", "500 g") is True
        assert compare_quantities("500g", "500 grams") is True
        assert compare_quantities("1 kg", "1000 g") is True
        assert compare_quantities("1.5 L", "1500 ml") is True
        assert compare_quantities("500g", "600g") is False
        assert compare_quantities("500g", "500 ml") is False  # different dimensions

    # ------------------ Text Normalizer ------------------ #
    def test_normalize_text(self):
        assert normalize_text("  ABC   Foods  ") == "abc foods"
        assert normalize_text("Demo, Inc.") == "demo, inc."
        assert normalize_text("INDIA") == "india"
        assert normalize_text(None) is None
        assert normalize_text("   ") is None

    def test_are_texts_equivalent(self):
        assert are_texts_equivalent("ABC Foods Ltd", "abc foods ltd") is True
        assert are_texts_equivalent("  Demo  Product  ", "demo product") is True
        assert are_texts_equivalent("India", "india.") is True or are_texts_equivalent("India", "india") is True
        assert are_texts_equivalent("ABC Foods", "XYZ Foods") is False
