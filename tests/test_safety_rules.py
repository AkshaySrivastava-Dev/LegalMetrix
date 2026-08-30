"""
Unit tests for Configurable Product Safety Rules Engine.
"""

import pytest
from ai.safety_rules import evaluate_product_safety, SAFETY_RULES_REGISTRY


def test_maaza_safety_alert():
    """Verify Maaza and its aliases trigger configured safety ALERT."""
    # Test canonical
    res = evaluate_product_safety(brand="Maaza")
    assert res["status"] == "ALERT"
    assert "Do not consume" in res["message"]
    assert res["source"] == "configured_demo_rule"
    assert res["rule_id"] == "SAFETY-DEMO-MAAZA"

    # Test lowercase
    res2 = evaluate_product_safety(brand="maaza")
    assert res2["status"] == "ALERT"

    # Test Mazza alias
    res3 = evaluate_product_safety(brand="Mazza Refresh")
    assert res3["status"] == "ALERT"

    # Test in fields dict
    res4 = evaluate_product_safety(fields={"brand": {"value": "MAAZA"}})
    assert res4["status"] == "ALERT"


def test_pepsi_safety_alert():
    """Verify Pepsi and its OCR variations trigger configured safety ALERT."""
    res = evaluate_product_safety(brand="Pepsi")
    assert res["status"] == "ALERT"
    assert "Do not consume" in res["message"]
    assert res["source"] == "configured_demo_rule"
    assert res["rule_id"] == "SAFETY-DEMO-PEPSI"

    # Test OCR variation Pepsl
    res2 = evaluate_product_safety(brand="PEPSL")
    assert res2["status"] == "ALERT"

    # Test in fields dict
    res3 = evaluate_product_safety(fields={"brand": {"value": "pepsi-cola"}})
    assert res3["status"] == "ALERT"


def test_too_yumm_safety_safe():
    """Verify Too Yumm / Chips trigger configured SAFE_STATUS."""
    res = evaluate_product_safety(brand="Too Yumm")
    assert res["status"] == "SAFE_STATUS"
    assert "No safety alert identified" in res["message"]
    assert res["source"] == "configured_demo_rule"
    assert res["rule_id"] == "SAFETY-DEMO-TOO-YUMM"

    # Test identifying phrases
    res2 = evaluate_product_safety(product_name="ASC Chips")
    assert res2["status"] == "SAFE_STATUS"

    res3 = evaluate_product_safety(product_name="American Style Cream & Onion")
    assert res3["status"] == "SAFE_STATUS"


def test_badam_milk_safety_safe():
    """Verify Badam Milk / Badamm trigger configured SAFE_STATUS."""
    res = evaluate_product_safety(brand="Badam Milk")
    assert res["status"] == "SAFE_STATUS"
    assert "No safety alert identified" in res["message"]
    assert res["source"] == "configured_demo_rule"
    assert res["rule_id"] == "SAFETY-DEMO-BADAM-MILK"

    # Test Badamm alias
    res2 = evaluate_product_safety(brand="BADAMM")
    assert res2["status"] == "SAFE_STATUS"


def test_unknown_product_no_rule():
    """Verify unconfigured products return NO_RULE without making safety assumptions."""
    res = evaluate_product_safety(brand="Amul Butter")
    assert res["status"] == "NO_RULE"
    assert res["message"] == "No configured safety alert for this product."
    assert res["source"] is None
    assert res["rule_id"] is None

    res2 = evaluate_product_safety(brand="Britannia Good Day", product_name="Butter Cookies")
    assert res2["status"] == "NO_RULE"

    res3 = evaluate_product_safety()
    assert res3["status"] == "NO_RULE"
