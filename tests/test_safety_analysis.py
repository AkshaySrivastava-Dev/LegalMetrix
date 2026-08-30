"""
Unit Tests for Safety Watchlist and Ingredient Analysis.
"""

import pytest
from ai.safety import extract_ingredients_from_ocr, analyze_safety_watchlist


class TestSafetyAnalysis:
    """Test suite for ingredient extraction and safety watchlist analysis."""

    def test_extract_ingredients_standard(self):
        ocr_results = [
            {"text": "PREMIUM MANGO NECTAR", "confidence": 98.0},
            {"text": "INGREDIENTS: Water, Mango Pulp (19.5%), Sugar, Acidity Regulator (INS 330), Antioxidant (INS 300).", "confidence": 95.0},
            {"text": "NET QTY: 200 ml", "confidence": 96.0}
        ]
        raw_text, items = extract_ingredients_from_ocr(ocr_results)
        assert raw_text is not None
        assert "Mango Pulp" in raw_text
        assert len(items) >= 4
        assert any("Mango Pulp" in it for it in items)

    def test_extract_ingredients_multiline(self):
        ocr_results = [
            {"text": "CRUNCHY BISCUITS", "confidence": 98.0},
            {"text": "INGREDIENTS: Refined Wheat Flour (Maida),", "confidence": 94.0},
            {"text": "Sugar, Palm Oil, Invert Syrup, Salt,", "confidence": 92.0},
            {"text": "Emulsifier (INS 322), Added Flavours.", "confidence": 90.0},
            {"text": "MFD: 10/2026", "confidence": 99.0}
        ]
        raw_text, items = extract_ingredients_from_ocr(ocr_results)
        assert raw_text is not None
        assert len(items) >= 5
        assert any("Wheat Flour" in it for it in items)

    def test_extract_ingredients_empty(self):
        raw_text, items = extract_ingredients_from_ocr([])
        assert raw_text is None
        assert items == []

    def test_safety_watchlist_msg_trigger(self):
        ingredients_text = "Noodles: Wheat Flour, Palm Oil. Tastemaker: Salt, Sugar, Monosodium Glutamate (INS 621), Spices."
        res = analyze_safety_watchlist(ingredients_text)
        assert res["status"] == "SAFETY_REVIEW_REQUIRED"
        assert res["review_required"] is True
        assert any(c["code"] == "INS 621 / E621" for c in res["flagged_components"])
        # Verify neutral wording
        for flag in res["flagged_components"]:
            assert "unsafe" not in flag["reason"].lower()
            assert "harmful" not in flag["reason"].lower()
            assert "statutory" in flag["reason"].lower() or "mandatory" in flag["reason"].lower() or "advisory" in flag["reason"].lower()

    def test_safety_watchlist_sweetener_trigger(self):
        ingredients_text = "Carbonated Water, Acidity Regulators, Aspartame (INS 951), Caffeine, Preservative (INS 211)."
        res = analyze_safety_watchlist(ingredients_text)
        assert res["status"] == "SAFETY_REVIEW_REQUIRED"
        assert len(res["flagged_components"]) >= 2  # Aspartame & Sodium Benzoate
        codes = [c["code"] for c in res["flagged_components"]]
        assert "INS 951 / E951" in codes
        assert "INS 211 / E211" in codes

    def test_safety_watchlist_clean_ingredients(self):
        ingredients_text = "100% Pure Organic Cold-Pressed Coconut Oil."
        res = analyze_safety_watchlist(ingredients_text)
        assert res["status"] == "COMPLIANT_DECLARATION"
        assert res["review_required"] is False
        assert len(res["flagged_components"]) == 0
