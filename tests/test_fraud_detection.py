"""
Unit tests for Fraud / Anomaly Detection and Human Review Layer.
"""

import pytest
from ai.fraud_detection import evaluate_fraud_and_review, PRODUCT_REFERENCE_RULES


def test_case_1_badam_milk_no_mismatch():
    """Case 1: Badam Milk with all extracted values matching expected reference."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "200", "unit": "ml"},
        "manufacturer": {"value": "JERSEY"},
        "country_of_origin": {"value": "India"},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "NO_MISMATCH"
    assert res["review_required"] is False
    assert len(res["mismatches"]) == 0


def test_case_2_badam_milk_net_quantity_mismatch():
    """Case 2: Badam Milk with net quantity mismatch (250 ml != 200 ml)."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "250", "unit": "ml", "source_view": "front", "confidence": 0.92},
        "manufacturer": {"value": "JERSEY"},
        "country_of_origin": {"value": "India"},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "POTENTIAL_FRAUD"
    assert len(res["mismatches"]) >= 1
    m = next(item for item in res["mismatches"] if item["field"] == "net_quantity")
    assert "200" in m["expected"]
    assert "250" in m["actual"]


def test_case_3_badam_milk_manufacturer_mismatch():
    """Case 3: Badam Milk with manufacturer mismatch (ABC Ltd != JERSEY)."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "200", "unit": "ml"},
        "manufacturer": {"value": "ABC Ltd", "source_view": "back", "confidence": 0.90},
        "country_of_origin": {"value": "India"},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "POTENTIAL_FRAUD"
    m = next(item for item in res["mismatches"] if item["field"] == "manufacturer")
    assert m["expected"] == "JERSEY"
    assert m["actual"] == "ABC Ltd"


def test_case_4_badam_milk_country_mismatch():
    """Case 4: Badam Milk with country mismatch (USA != India)."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "200", "unit": "ml"},
        "manufacturer": {"value": "JERSEY"},
        "country_of_origin": {"value": "USA", "source_view": "back", "confidence": 0.93},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "POTENTIAL_FRAUD"
    m = next(item for item in res["mismatches"] if item["field"] == "country_of_origin")
    assert m["expected"] == "India"
    assert m["actual"] == "USA"


def test_case_5_badam_milk_missing_mfg_date():
    """Case 5: Badam Milk with missing manufacturing date -> MANUAL_REVIEW."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "200", "unit": "ml"},
        "manufacturer": {"value": "JERSEY"},
        "country_of_origin": {"value": "India"},
        "manufacturing_date": {"value": None},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "MANUAL_REVIEW"
    assert res["review_required"] is True
    assert "Manufacturing date" in res["reason"]


def test_case_6_badam_milk_missing_expiry_date():
    """Case 6: Badam Milk with missing expiry date -> MANUAL_REVIEW."""
    fields = {
        "brand": {"value": "Badam Milk"},
        "net_quantity": {"value": "200", "unit": "ml"},
        "manufacturer": {"value": "JERSEY"},
        "country_of_origin": {"value": "India"},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": None},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] == "MANUAL_REVIEW"
    assert res["review_required"] is True
    assert "Expiry date" in res["reason"]


def test_case_7_badam_milk_missing_fields_not_fraud():
    """Case 7: Missing fields from OCR are NOT automatically flagged as fraud."""
    fields = {
        "brand": {"value": None},
        "net_quantity": {"value": None},
        "manufacturer": {"value": None},
        "country_of_origin": {"value": None},
        "manufacturing_date": {"value": "01/05/2026", "confidence": 0.95},
        "expiry_date": {"value": "01/11/2026", "confidence": 0.94},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Badam Milk")
    assert res["status"] in ["INSUFFICIENT_EVIDENCE", "MANUAL_REVIEW"]
    assert res["status"] != "POTENTIAL_FRAUD"
    assert len(res["mismatches"]) == 0


def test_case_8_unknown_product():
    """Case 8: Unknown unconfigured product returns NO_REFERENCE."""
    fields = {
        "brand": {"value": "Generic Brand"},
        "net_quantity": {"value": "500", "unit": "g"},
        "manufacturing_date": {"value": "10/2026", "confidence": 0.90},
        "expiry_date": {"value": "10/2027", "confidence": 0.90},
    }
    res = evaluate_fraud_and_review(fields=fields, brand="Generic Brand")
    assert res["status"] == "NO_REFERENCE"
    assert res["review_required"] is False
