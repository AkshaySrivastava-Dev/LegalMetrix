"""
Unit tests for FSSAI Status & Verification Engine.
"""

import pytest
from ai.fssai_verification import evaluate_fssai_status, FSSAI_REFERENCE_REGISTRY


def test_pepsi_fssai_demo_verified():
    """Verify Pepsi returns DEMO_VERIFIED with license 10014064000435."""
    res = evaluate_fssai_status(category="beverage", brand="Pepsi")
    assert res["status"] == "DEMO_VERIFIED"
    assert res["license_number"] == "10014064000435"
    assert res["source"] == "demo_reference"


def test_maaza_fssai_demo_verified():
    """Verify Maaza returns DEMO_VERIFIED with license 10012011000620."""
    res = evaluate_fssai_status(category="beverage", brand="Maaza")
    assert res["status"] == "DEMO_VERIFIED"
    assert res["license_number"] == "10012011000620"
    assert res["source"] == "demo_reference"


def test_too_yumm_fssai_demo_verified():
    """Verify Too Yumm returns DEMO_VERIFIED with license 10017031002079."""
    res = evaluate_fssai_status(category="food", brand="Too Yumm")
    assert res["status"] == "DEMO_VERIFIED"
    assert res["license_number"] == "10017031002079"
    assert res["source"] == "demo_reference"


def test_badam_milk_fssai_demo_verified():
    """Verify Badam Milk returns DEMO_VERIFIED with license 10014047000258."""
    res = evaluate_fssai_status(category="dairy", brand="Badam Milk")
    assert res["status"] == "DEMO_VERIFIED"
    assert res["license_number"] == "10014047000258"
    assert res["source"] == "demo_reference"


def test_unverified_food_with_ocr_license():
    """Verify food product with OCR license but no verified reference returns NOT_VERIFIED."""
    fields = {
        "fssai_license_number": {"value": "11521000000000", "source_view": "back", "confidence": 0.95}
    }
    res = evaluate_fssai_status(category="food", brand="Generic Cookies", fields=fields)
    assert res["status"] == "NOT_VERIFIED"
    assert res["license_number"] == "11521000000000"
    assert res["source"] == "package_ocr"


def test_food_without_fssai_evidence():
    """Verify food product without license returns NOT_VERIFIED and null license."""
    res = evaluate_fssai_status(category="food", brand="Unbranded Bakery")
    assert res["status"] == "NOT_VERIFIED"
    assert res["license_number"] is None
    assert res["source"] is None


def test_non_food_not_applicable():
    """Verify non-food products return NOT_APPLICABLE."""
    res1 = evaluate_fssai_status(category="personal_care", brand="Nivea")
    assert res1["status"] == "NOT_APPLICABLE"
    assert res1["license_number"] is None

    res2 = evaluate_fssai_status(category="household", brand="Surf Excel")
    assert res2["status"] == "NOT_APPLICABLE"
