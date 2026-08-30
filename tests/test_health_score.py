"""
Unit tests for Prototype Health Score Engine.
"""

import pytest
from ai.health_score import evaluate_health_score, HEALTH_SCORES_REGISTRY


def test_pepsi_health_score():
    """Verify Pepsi returns exactly 5/10 and NOT_HEALTHY."""
    res = evaluate_health_score(brand="Pepsi")
    assert res["score"] == 5.0
    assert res["out_of"] == 10
    assert res["status"] == "NOT_HEALTHY"
    assert res["source"] == "demo_product_rule"
    assert res["label"] == "Demo Health Score"

    # OCR Variation
    res2 = evaluate_health_score(brand="PEPSL")
    assert res2["score"] == 5.0
    assert res2["status"] == "NOT_HEALTHY"


def test_maaza_health_score():
    """Verify Maaza returns exactly 6/10 and NOT_HEALTHY."""
    res = evaluate_health_score(brand="Maaza")
    assert res["score"] == 6.0
    assert res["out_of"] == 10
    assert res["status"] == "NOT_HEALTHY"
    assert res["source"] == "demo_product_rule"

    # Mazza alias
    res2 = evaluate_health_score(brand="Mazza Refresh")
    assert res2["score"] == 6.0
    assert res2["status"] == "NOT_HEALTHY"


def test_too_yumm_health_score():
    """Verify Too Yumm / Chips returns exactly 8/10 and HEALTHY (> 7)."""
    res = evaluate_health_score(brand="Too Yumm")
    assert res["score"] == 8.0
    assert res["out_of"] == 10
    assert res["status"] == "HEALTHY"
    assert res["source"] == "demo_product_rule"

    # Identifying phrase
    res2 = evaluate_health_score(product_name="ASC Chips")
    assert res2["score"] == 8.0
    assert res2["status"] == "HEALTHY"

    res3 = evaluate_health_score(product_name="American Style Cream & Onion")
    assert res3["score"] == 8.0
    assert res3["status"] == "HEALTHY"


def test_badam_milk_health_score():
    """Verify Badam Milk returns exactly 7/10 and NOT_HEALTHY (threshold is strictly > 7)."""
    res = evaluate_health_score(brand="Badam Milk")
    assert res["score"] == 7.0
    assert res["out_of"] == 10
    assert res["status"] == "NOT_HEALTHY"
    assert res["source"] == "demo_product_rule"

    # Alias
    res2 = evaluate_health_score(brand="BADAMM")
    assert res2["score"] == 7.0
    assert res2["status"] == "NOT_HEALTHY"


def test_unknown_product_random_score():
    """Verify unknown products get a random score (0-10) with source demo_random."""
    res = evaluate_health_score(brand="Amul Ghee")
    assert 0.0 <= res["score"] <= 10.0
    assert res["out_of"] == 10
    assert res["source"] == "demo_random"
    assert res["status"] == ("HEALTHY" if res["score"] > 7.0 else "NOT_HEALTHY")
    assert res["label"] == "Demo Health Score"
