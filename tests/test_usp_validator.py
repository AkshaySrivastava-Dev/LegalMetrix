"""
Unit Tests for Statutory Unit Sale Price (USP) Validator.
Tests mathematical accuracy, standard units (g, kg, ml, L, pieces), decimal calculations, and error cases.
"""

import pytest
from rules.engine.validators import calculate_unit_sale_price, validate_unit_sale_price


class TestUnitSalePriceValidator:
    def test_calculate_usp_grams(self):
        # 200g for Rs. 90 -> Rs. 0.45 / g (or Rs. 450 / kg)
        result = calculate_unit_sale_price(mrp="90.00", net_quantity="200 g")
        assert result is not None
        assert result["unit_price"] == 0.45
        assert result["standard_unit"] == "g"
        assert "₹0.45 / g" in result["display_string"]

    def test_calculate_usp_kg(self):
        # 5 kg for Rs. 250 -> Rs. 50 / kg
        result = calculate_unit_sale_price(mrp="250.00", net_quantity="5 kg")
        assert result is not None
        assert result["unit_price"] == 50.0
        assert result["standard_unit"] == "kg"
        assert "₹50.00 / kg" in result["display_string"]

    def test_calculate_usp_millilitres(self):
        # 750 ml for Rs. 150 -> Rs. 0.20 / ml
        result = calculate_unit_sale_price(mrp=150.0, net_quantity="750 ml")
        assert result is not None
        assert result["unit_price"] == 0.2
        assert result["standard_unit"] == "ml"
        assert "₹0.20 / ml" in result["display_string"]

    def test_calculate_usp_litres(self):
        # 2 L for Rs. 180 -> Rs. 90 / L
        result = calculate_unit_sale_price(mrp="180", net_quantity="2 L")
        assert result is not None
        assert result["unit_price"] == 90.0
        assert result["standard_unit"] == "L"
        assert "₹90.00 / L" in result["display_string"]

    def test_calculate_usp_pieces(self):
        # 10 pcs for Rs. 100 -> Rs. 10 / piece
        result = calculate_unit_sale_price(mrp="100.00", net_quantity="10 pcs")
        assert result is not None
        assert result["unit_price"] == 10.0
        assert result["standard_unit"] == "piece"

    def test_calculate_usp_invalid_inputs(self):
        assert calculate_unit_sale_price(mrp=None, net_quantity="100 g") is None
        assert calculate_unit_sale_price(mrp="-50", net_quantity="100 g") is None
        assert calculate_unit_sale_price(mrp="50", net_quantity=None) is None
        assert calculate_unit_sale_price(mrp="50", net_quantity="0 g") is None

    def test_validate_usp_matching(self):
        # Valid matching USP
        valid, msg, calc = validate_unit_sale_price(mrp="90.00", net_quantity="200 g", declared_usp="0.45")
        assert valid is True
        assert "matches statutory rate" in msg
        assert calc["unit_price"] == 0.45

    def test_validate_usp_matching_kg_equivalent(self):
        # Declared as 450 per kg for 200g @ Rs 90
        valid, msg, calc = validate_unit_sale_price(mrp="90.00", net_quantity="200 g", declared_usp="450.00")
        assert valid is True
        assert "matches statutory rate" in msg

    def test_validate_usp_mismatch(self):
        # Declared as 0.75 when actual is 0.45
        valid, msg, calc = validate_unit_sale_price(mrp="90.00", net_quantity="200 g", declared_usp="0.75")
        assert valid is False
        assert "does not match calculated statutory rate" in msg

    def test_validate_usp_missing_declaration(self):
        valid, msg, calc = validate_unit_sale_price(mrp="90.00", net_quantity="200 g", declared_usp=None)
        assert valid is False
        assert "USP not declared on package" in msg
