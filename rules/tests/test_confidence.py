"""
Unit Tests for LegalMetrix Confidence Routing.
"""

import pytest
from rules.engine.confidence_router import (
    ConfidenceTier,
    route_confidence,
)


class TestConfidenceRouter:
    def test_auto_threshold_boundaries(self):
        # 100% -> AUTO
        r100 = route_confidence(100)
        assert r100["tier"] == ConfidenceTier.AUTO.value
        assert r100["requires_manual_review"] is False
        assert r100["review_recommended"] is False

        # 90% boundary -> AUTO
        r90 = route_confidence(90)
        assert r90["tier"] == ConfidenceTier.AUTO.value
        assert r90["requires_manual_review"] is False

    def test_review_recommended_boundaries(self):
        # 89.9% -> REVIEW_RECOMMENDED
        r89 = route_confidence(89.9)
        assert r89["tier"] == ConfidenceTier.REVIEW_RECOMMENDED.value
        assert r89["requires_manual_review"] is False
        assert r89["review_recommended"] is True

        # 60% boundary -> REVIEW_RECOMMENDED
        r60 = route_confidence(60)
        assert r60["tier"] == ConfidenceTier.REVIEW_RECOMMENDED.value
        assert r60["requires_manual_review"] is False
        assert r60["review_recommended"] is True

    def test_manual_verification_boundaries(self):
        # 59.9% -> MANUAL_VERIFICATION
        r59 = route_confidence(59.9)
        assert r59["tier"] == ConfidenceTier.MANUAL_VERIFICATION.value
        assert r59["requires_manual_review"] is True

        # 0% -> MANUAL_VERIFICATION
        r0 = route_confidence(0)
        assert r0["tier"] == ConfidenceTier.MANUAL_VERIFICATION.value
        assert r0["requires_manual_review"] is True

    def test_missing_or_none_confidence(self):
        r_none = route_confidence(None)
        assert r_none["tier"] == ConfidenceTier.MANUAL_VERIFICATION.value
        assert r_none["requires_manual_review"] is True
        assert r_none["confidence"] == 0.0

    def test_invalid_type_confidence(self):
        r_str = route_confidence("invalid_conf")
        assert r_str["tier"] == ConfidenceTier.MANUAL_VERIFICATION.value
        assert r_str["requires_manual_review"] is True

    def test_clamping_ranges(self):
        r_over = route_confidence(125.0)
        assert r_over["confidence"] == 100.0
        assert r_over["tier"] == ConfidenceTier.AUTO.value

        r_under = route_confidence(-10.0)
        assert r_under["confidence"] == 0.0
        assert r_under["tier"] == ConfidenceTier.MANUAL_VERIFICATION.value
