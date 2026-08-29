"""
Golden Test Scenarios for LegalMetrix — Member 4 Engine.

Tests the five fundamental golden demonstration cases:
1. Case 1: Fully Compliant Packaged Product
2. Case 2: Potential Non-Compliance (Deterministic Rule Failure)
3. Case 3: Low Confidence Extraction (Officer Review Required)
4. Reconciliation Golden Case: Physical ₹50 vs Online ₹60
5. Historical Golden Case: Previous ₹50 vs Current ₹60
"""

import pytest
from reconciliation.comparator import (
    ComparisonResult,
    HistoricalStatus,
    compare_historical,
    compare_product,
)
from rules.engine import (
    FindingResult,
    OverallComplianceStatus,
    evaluate_compliance,
)


class TestGoldenScenarios:
    # ------------------ CASE 1 — COMPLIANT ------------------ #
    def test_golden_case_1_compliant(self):
        """
        All required declarations extracted with high confidence (>=90%).
        Expected: COMPLIANT
        """
        extracted_data = {
            "product_name": "ABC Premium Biscuits",
            "net_quantity": "500g",
            "mrp": "₹50",
            "manufacturer": "ABC Foods Pvt Ltd, Mumbai, India",
            "country_of_origin": "India",
            "date_of_manufacture": "08/2026",
            "consumer_care": "help@abcfoods.com, 1800-123-456",
        }
        confidence_data = {
            "product_name": 98.0,
            "net_quantity": 95.0,
            "mrp": 96.0,
            "manufacturer": 92.0,
            "country_of_origin": 97.0,
            "date_of_manufacture": 91.0,
            "consumer_care": 90.0,
        }
        evidence_data = {
            "product_name": {"frame_id": "frame_01"},
            "net_quantity": {"frame_id": "frame_01"},
            "mrp": {"frame_id": "frame_02"},
            "manufacturer": {"frame_id": "frame_03"},
            "country_of_origin": {"frame_id": "frame_03"},
            "date_of_manufacture": {"frame_id": "frame_02"},
            "consumer_care": {"frame_id": "frame_04"},
        }

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted_data,
            confidence_data=confidence_data,
            evidence_data=evidence_data,
        )

        assert result["overall_status"] == OverallComplianceStatus.COMPLIANT.value
        assert result["failed_count"] == 0
        assert result["uncertain_count"] == 0
        assert result["passed_count"] == 7
        assert len(result["manual_reviews"]) == 0

        # Verify explainability on all findings
        for finding in result["findings"]:
            assert finding["result"] == FindingResult.PASS.value
            assert finding["evidence"] is not None
            assert finding["rule_id"].startswith("RULE-FOOD-")
            assert len(finding["reason"]) > 0

    # ------------------ CASE 2 — POTENTIAL NON-COMPLIANCE ------------------ #
    def test_golden_case_2_potential_non_compliance(self):
        """
        Deterministic rule fails: Mandatory MRP and Country of Origin declarations are missing.
        Expected: NON_COMPLIANT
        """
        extracted_data = {
            "product_name": "ABC Premium Biscuits",
            "net_quantity": "500g",
            # mrp is missing
            "manufacturer": "ABC Foods Pvt Ltd",
            # country_of_origin is missing
            "date_of_manufacture": "08/2026",
            "consumer_care": "help@abcfoods.com",
        }
        confidence_data = {
            "product_name": 98.0,
            "net_quantity": 95.0,
            "manufacturer": 92.0,
            "date_of_manufacture": 91.0,
            "consumer_care": 90.0,
        }
        evidence_data = {
            "product_name": "frame_01",
            "net_quantity": "frame_01",
            "manufacturer": "frame_03",
        }

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted_data,
            confidence_data=confidence_data,
            evidence_data=evidence_data,
        )

        assert result["overall_status"] == OverallComplianceStatus.NON_COMPLIANT.value
        assert result["failed_count"] >= 2
        assert "Non-compliance detected" in result["summary"]

        mrp_finding = next(f for f in result["findings"] if f["field"] == "mrp")
        assert mrp_finding["result"] == FindingResult.FAIL.value
        assert mrp_finding["extracted_value"] is None
        assert "missing" in mrp_finding["reason"].lower()

    # ------------------ CASE 3 — LOW CONFIDENCE (OFFICER REVIEW) ------------------ #
    def test_golden_case_3_low_confidence(self):
        """
        Manufacturer extraction confidence is low (43% < 60%).
        Expected: NEEDS_REVIEW with Manual Review structure populated.
        """
        extracted_data = {
            "product_name": "ABC Biscuits",
            "net_quantity": "500g",
            "mrp": "₹50",
            "manufacturer": "ABC Foods",
            "country_of_origin": "India",
            "date_of_manufacture": "08/2026",
            "consumer_care": "care@abcfoods.com",
        }
        confidence_data = {
            "product_name": 98.0,
            "mrp": 96.0,
            "net_quantity": 94.0,
            "manufacturer": 43.0,  # Below threshold
            "country_of_origin": 92.0,
            "date_of_manufacture": 95.0,
            "consumer_care": 90.0,
        }
        evidence_data = {
            "product_name": "frame_01",
            "mrp": "frame_02",
            "net_quantity": "frame_02",
            "manufacturer": "frame_03",
        }

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted_data,
            confidence_data=confidence_data,
            evidence_data=evidence_data,
        )

        assert result["overall_status"] == OverallComplianceStatus.NEEDS_REVIEW.value
        assert result["uncertain_count"] == 1
        assert result["failed_count"] == 0

        # Verify manual review information is present
        assert len(result["manual_reviews"]) == 1
        m_review = result["manual_reviews"][0]
        assert m_review["field"] == "manufacturer"
        assert m_review["ai_value"] == "ABC Foods"
        assert m_review["confidence"] == 43.0
        assert m_review["evidence"] == {"frame_id": "frame_03"}
        assert m_review["requires_manual_review"] is True

    # ------------------ RECONCILIATION GOLDEN CASE ------------------ #
    def test_reconciliation_golden_case(self):
        """
        Physical: Demo Product, MRP: ₹50, Net Quantity: 500g, Manufacturer: Demo Foods, Country: India
        Online:   Demo Product, MRP: ₹60, Net Quantity: 500 g, Manufacturer: Demo Foods, Country: India
        Expected:
            MRP -> MISMATCH
            Net quantity -> MATCH
            Manufacturer -> MATCH
            Country of origin -> MATCH
            Overall -> MISMATCH
            Message: "Potential mismatch detected — officer review recommended."
        """
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

        fields = result["fields"]
        assert fields["mrp"]["result"] == ComparisonResult.MISMATCH.value
        assert fields["net_quantity"]["result"] == ComparisonResult.MATCH.value
        assert fields["manufacturer"]["result"] == ComparisonResult.MATCH.value
        assert fields["country_of_origin"]["result"] == ComparisonResult.MATCH.value

    # ------------------ HISTORICAL GOLDEN CASE ------------------ #
    def test_historical_golden_case(self):
        """
        Previous: Demo, Demo Product, food, 500g, MRP: ₹50
        Current:  Demo, Demo Product, food, 500g, MRP: ₹60
        Expected:
            status -> CHANGE_DETECTED
            Message: "Change detected — officer review recommended."
        """
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
        assert len(result["changes"]) == 1
        assert result["changes"][0]["field"] == "mrp"
        assert result["changes"][0]["previous"] == "₹50"
        assert result["changes"][0]["current"] == "₹60"
        assert result["changes"][0]["reason"] == "Previous MRP is ₹50.00 vs Current MRP is ₹60.00"
