"""
Unit Tests for LegalMetrix Product Reconciliation & Mismatch Detection.
"""

import pytest
from reconciliation.comparator.field_comparator import (
    ComparisonResult,
    compare_field,
)
from reconciliation.comparator.mismatch_detector import (
    compare_product,
)


class TestProductComparator:
    # ------------------ Field Comparison Tests ------------------ #
    def test_compare_field_mrp_match(self):
        res = compare_field("mrp", "₹50", "Rs. 50.00")
        assert res["result"] == ComparisonResult.MATCH.value
        assert "match" in res["reason"].lower()

    def test_compare_field_mrp_mismatch(self):
        res = compare_field("mrp", "₹50", "₹60")
        assert res["result"] == ComparisonResult.MISMATCH.value
        assert "50.00" in res["reason"] and "60.00" in res["reason"]

    def test_compare_field_quantity_match(self):
        res = compare_field("net_quantity", "500g", "500 grams")
        assert res["result"] == ComparisonResult.MATCH.value

    def test_compare_field_quantity_mismatch(self):
        res = compare_field("net_quantity", "500g", "750g")
        assert res["result"] == ComparisonResult.MISMATCH.value

    def test_compare_field_text_match(self):
        res = compare_field("manufacturer", "Demo Foods Pvt Ltd", "demo foods pvt ltd")
        assert res["result"] == ComparisonResult.MATCH.value

    def test_compare_field_text_mismatch(self):
        res = compare_field("manufacturer", "Demo Foods", "Other Foods")
        assert res["result"] == ComparisonResult.MISMATCH.value

    def test_compare_field_unavailable(self):
        res_both = compare_field("country_of_origin", None, None)
        assert res_both["result"] == ComparisonResult.UNAVAILABLE.value

        res_one = compare_field("country_of_origin", "India", None)
        assert res_one["result"] == ComparisonResult.UNAVAILABLE.value

    # ------------------ Product Comparison & Golden Case ------------------ #
    def test_compare_product_golden_case(self):
        physical = {
            "product_name": "Demo Product",
            "mrp": "₹50",
            "net_quantity": "500g",
            "manufacturer": "Demo Foods",
            "country_of_origin": "India",
        }
        online = {
            "product_name": "Demo Product",
            "mrp": "₹60",
            "net_quantity": "500 g",
            "manufacturer": "Demo Foods",
            "country_of_origin": "India",
        }

        result = compare_product(physical, online)

        assert result["overall"] == ComparisonResult.MISMATCH.value
        assert result["message"] == "Potential mismatch detected — officer review recommended."
        assert result["mismatches_count"] == 1
        assert result["matches_count"] == 4

        fields = result["fields"]
        assert fields["product_name"]["result"] == ComparisonResult.MATCH.value
        assert fields["mrp"]["result"] == ComparisonResult.MISMATCH.value
        assert fields["net_quantity"]["result"] == ComparisonResult.MATCH.value
        assert fields["manufacturer"]["result"] == ComparisonResult.MATCH.value
        assert fields["country_of_origin"]["result"] == ComparisonResult.MATCH.value

    def test_compare_product_complete_match(self):
        physical = {
            "product_name": "ABC Biscuits",
            "mrp": "₹50",
            "net_quantity": "500g",
            "manufacturer": "ABC Foods Ltd",
            "country_of_origin": "India",
        }
        online = {
            "product_name": "ABC Biscuits",
            "mrp": "Rs 50",
            "net_quantity": "500 grams",
            "manufacturer": "abc foods ltd",
            "country_of_origin": "India",
        }

        result = compare_product(physical, online)

        assert result["overall"] == ComparisonResult.MATCH.value
        assert result["mismatches_count"] == 0
        assert result["matches_count"] >= 5
        assert "match online catalog" in result["message"]

    def test_compare_product_all_unavailable(self):
        result = compare_product({}, {})
        assert result["overall"] == ComparisonResult.UNAVAILABLE.value
        assert result["matches_count"] == 0
        assert result["mismatches_count"] == 0
