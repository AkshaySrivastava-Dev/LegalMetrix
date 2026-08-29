"""
Unit Tests for LegalMetrix Deterministic Validators.
"""

import pytest
from rules.engine.validators import (
    execute_validator,
    validate_exact,
    validate_numeric,
    validate_pattern,
    validate_presence,
    validate_range,
)


class TestValidators:
    # ------------------ Presence Validator ------------------ #
    def test_validate_presence_valid(self):
        assert validate_presence("ABC Biscuits") is True
        assert validate_presence("₹50") is True
        assert validate_presence(50) is True
        assert validate_presence(0) is True
        assert validate_presence(False) is True
        assert validate_presence(["item1"]) is True
        assert validate_presence({"key": "val"}) is True

    def test_validate_presence_invalid(self):
        assert validate_presence(None) is False
        assert validate_presence("") is False
        assert validate_presence("   ") is False
        assert validate_presence("\t\n") is False
        assert validate_presence([]) is False
        assert validate_presence({}) is False

    # ------------------ Exact Validator ------------------ #
    def test_validate_exact_case_insensitive(self):
        assert validate_exact("India", "india", case_sensitive=False) is True
        assert validate_exact("  ABC Foods  ", "abc foods", case_sensitive=False) is True
        assert validate_exact("India", "USA", case_sensitive=False) is False

    def test_validate_exact_case_sensitive(self):
        assert validate_exact("India", "India", case_sensitive=True) is True
        assert validate_exact("India", "india", case_sensitive=True) is False

    def test_validate_exact_missing(self):
        assert validate_exact(None, "India") is False
        assert validate_exact("India", None) is False
        assert validate_exact("", "India") is False

    # ------------------ Pattern Validator ------------------ #
    def test_validate_pattern_valid(self):
        # Match YYYY-MM or MM/YYYY format
        assert validate_pattern("08/2026", r"^\d{2}/\d{4}$") is True
        assert validate_pattern("BATCH-1029", r"^BATCH-\d+$") is True

    def test_validate_pattern_invalid(self):
        assert validate_pattern("Invalid-Batch", r"^BATCH-\d+$") is False
        assert validate_pattern(None, r"^BATCH-\d+$") is False
        assert validate_pattern("", r"^BATCH-\d+$") is False

    # ------------------ Numeric Validator ------------------ #
    def test_validate_numeric_simple(self):
        assert validate_numeric(50) is True
        assert validate_numeric(50.5) is True
        assert validate_numeric("50") is True
        assert validate_numeric("₹50.00") is True
        assert validate_numeric("Rs. 100") is True

    def test_validate_numeric_bounds(self):
        assert validate_numeric("50", min_value=10, max_value=100) is True
        assert validate_numeric("5", min_value=10, max_value=100) is False
        assert validate_numeric("150", min_value=10, max_value=100) is False

    def test_validate_numeric_invalid_string(self):
        assert validate_numeric("NotANumber") is False
        assert validate_numeric(None) is False
        assert validate_numeric("") is False

    # ------------------ Range Validator ------------------ #
    def test_validate_range(self):
        assert validate_range(50, min_value=1, max_value=100) is True
        assert validate_range("₹50", min_value=1, max_value=100) is True
        assert validate_range(0, min_value=1, max_value=100) is False
        assert validate_range(150, min_value=1, max_value=100) is False

    # ------------------ Dispatcher Execution ------------------ #
    def test_execute_validator_presence(self):
        valid, reason = execute_validator({"type": "presence"}, "Present Value")
        assert valid is True
        assert "present" in reason.lower()

        valid, reason = execute_validator({"type": "presence"}, "")
        assert valid is False
        assert "missing" in reason.lower()

    def test_execute_validator_exact(self):
        valid, reason = execute_validator({"type": "exact", "expected_value": "India"}, "India")
        assert valid is True

        valid, reason = execute_validator({"type": "exact", "expected_value": "India"}, "China")
        assert valid is False

    def test_execute_validator_pattern(self):
        valid, reason = execute_validator({"type": "pattern", "pattern": r"^\d{10}$"}, "9876543210")
        assert valid is True

        valid, reason = execute_validator({"type": "pattern", "pattern": r"^\d{10}$"}, "abc")
        assert valid is False

    def test_execute_validator_unsupported(self):
        valid, reason = execute_validator({"type": "quantum_check"}, "value")
        assert valid is False
        assert "unsupported" in reason.lower()

    def test_execute_validator_none_config(self):
        valid, reason = execute_validator(None, "Any Value")
        assert valid is True

        valid, reason = execute_validator(None, None)
        assert valid is False
