"""
Unit Tests for LegalMetrix Compliance Rule Engine & Manual Review.
"""

import pytest
from rules.engine.manual_review import (
    ReviewAction,
    ReviewStatus,
    apply_manual_review,
    create_manual_review_item,
)
from rules.engine.rule_engine import (
    FindingResult,
    OverallComplianceStatus,
    evaluate_compliance,
)


class TestRuleEngine:
    def test_evaluate_compliance_all_valid(self):
        extracted = {
            "product_name": "ABC Biscuits",
            "net_quantity": "500g",
            "mrp": "₹50",
            "manufacturer": "ABC Foods Ltd, Mumbai",
            "country_of_origin": "India",
            "date_of_manufacture": "08/2026",
            "consumer_care": "care@abcfoods.com, 1800-111-222",
        }
        confidence = {k: 95.0 for k in extracted}
        evidence = {k: f"frame_0{i+1}" for i, k in enumerate(extracted)}

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted,
            confidence_data=confidence,
            evidence_data=evidence,
        )

        assert result["overall_status"] == OverallComplianceStatus.COMPLIANT.value
        assert result["failed_count"] == 0
        assert result["uncertain_count"] == 0
        assert result["passed_count"] == result["total_rules_evaluated"]
        assert len(result["manual_reviews"]) == 0
        assert len(result["findings"]) == result["total_rules_evaluated"]

        for f in result["findings"]:
            assert f["result"] == FindingResult.PASS.value
            assert f["evidence"] is not None

    def test_evaluate_compliance_missing_required_field_fails(self):
        # Missing mrp and manufacturer
        extracted = {
            "product_name": "ABC Biscuits",
            "net_quantity": "500g",
            "country_of_origin": "India",
            "date_of_manufacture": "08/2026",
            "consumer_care": "care@abcfoods.com",
        }
        confidence = {k: 95.0 for k in extracted}

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted,
            confidence_data=confidence,
        )

        assert result["overall_status"] == OverallComplianceStatus.NON_COMPLIANT.value
        assert result["failed_count"] >= 2
        assert "Non-compliance detected" in result["summary"]

        mrp_finding = next(f for f in result["findings"] if f["field"] == "mrp")
        assert mrp_finding["result"] == FindingResult.FAIL.value
        assert "missing" in mrp_finding["reason"].lower()

    def test_evaluate_compliance_low_confidence_routes_to_needs_review(self):
        extracted = {
            "product_name": "ABC Biscuits",
            "net_quantity": "500g",
            "mrp": "₹50",
            "manufacturer": "ABC Foods Ltd",
            "country_of_origin": "India",
            "date_of_manufacture": "08/2026",
            "consumer_care": "care@abcfoods.com",
        }
        # Manufacturer has low confidence 43%
        confidence = {
            "product_name": 98.0,
            "mrp": 96.0,
            "net_quantity": 94.0,
            "manufacturer": 43.0,
            "country_of_origin": 90.0,
            "date_of_manufacture": 92.0,
            "consumer_care": 91.0,
        }
        evidence = {
            "manufacturer": {"frame_id": "frame_03", "region": {"x": 120, "y": 240, "width": 300, "height": 80}}
        }

        result = evaluate_compliance(
            category="food",
            extracted_data=extracted,
            confidence_data=confidence,
            evidence_data=evidence,
        )

        assert result["overall_status"] == OverallComplianceStatus.NEEDS_REVIEW.value
        assert result["uncertain_count"] == 1
        assert result["failed_count"] == 0
        assert len(result["manual_reviews"]) == 1

        # Check manual review item
        review_item = result["manual_reviews"][0]
        assert review_item["field"] == "manufacturer"
        assert review_item["ai_value"] == "ABC Foods Ltd"
        assert review_item["confidence"] == 43.0
        assert review_item["requires_manual_review"] is True
        assert review_item["status"] == ReviewStatus.PENDING.value
        assert review_item["evidence"]["frame_id"] == "frame_03"
        assert review_item["evidence"]["region"]["width"] == 300

    def test_evidence_preservation_and_formatting(self):
        extracted = {"product_name": "Demo Soap"}
        confidence = {"product_name": 95.0}
        evidence = {"product_name": "frame_01"}

        result = evaluate_compliance("personal_care", extracted, confidence, evidence)
        prod_finding = result["findings"][0]
        assert prod_finding["evidence"] == {"frame_id": "frame_01"}

    # ------------------ Manual Review Lifecycle Tests ------------------ #
    def test_manual_review_confirm_action(self):
        item = create_manual_review_item(
            field="manufacturer",
            ai_value="ABC Foods Ltd",
            confidence=43.0,
            reason="Low OCR confidence",
            evidence="frame_03",
        )
        assert item["status"] == ReviewStatus.PENDING.value

        resolved = apply_manual_review(
            review_item=item,
            action=ReviewAction.CONFIRM,
            reviewer_id="OFFICER-742",
            notes="Label verified manually via frame_03",
        )

        assert resolved["status"] == ReviewStatus.COMPLETED.value
        assert resolved["action"] == "CONFIRM"
        assert resolved["reviewer_id"] == "OFFICER-742"
        assert resolved["ai_value"] == "ABC Foods Ltd"  # Original preserved
        assert resolved["effective_value"] == "ABC Foods Ltd"
        assert resolved["resolved_at"] is not None

    def test_manual_review_correct_action_preserves_original(self):
        item = create_manual_review_item(
            field="mrp",
            ai_value="₹5O",  # OCR typo: 'O' instead of '0'
            confidence=52.0,
            reason="Uncertain digit extraction",
            evidence="frame_02",
        )

        resolved = apply_manual_review(
            review_item=item,
            action=ReviewAction.CORRECT,
            reviewer_id="OFFICER-742",
            corrected_value="₹50",
            notes="Corrected OCR character 'O' to digit '0'",
        )

        assert resolved["status"] == ReviewStatus.COMPLETED.value
        assert resolved["action"] == "CORRECT"
        assert resolved["ai_value"] == "₹5O"  # Strict preservation
        assert resolved["corrected_value"] == "₹50"
        assert resolved["effective_value"] == "₹50"
        assert resolved["confidence"] == 52.0
        assert resolved["evidence"] == {"frame_id": "frame_02"} or resolved["evidence"] == "frame_02"

    def test_manual_review_mark_unreadable(self):
        item = create_manual_review_item(
            field="date_of_manufacture",
            ai_value="??/2026",
            confidence=30.0,
            reason="Ink smudged",
        )

        resolved = apply_manual_review(
            review_item=item,
            action=ReviewAction.MARK_UNREADABLE,
            reviewer_id="OFFICER-742",
            notes="Physical stamp completely smudged on packaging",
        )

        assert resolved["status"] == ReviewStatus.COMPLETED.value
        assert resolved["action"] == "MARK_UNREADABLE"
        assert resolved["effective_value"] is None
