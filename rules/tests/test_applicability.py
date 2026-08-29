"""
Unit Tests for LegalMetrix Rule Applicability & Category Selection.
"""

import json
import pytest
from pathlib import Path
from rules.engine.applicability import (
    CategoryNotFoundError,
    InvalidRuleDefinitionError,
    get_available_categories,
    get_rules_for_category,
    normalize_category_name,
)


class TestApplicability:
    def test_normalize_category_name(self):
        assert normalize_category_name("Food") == "food"
        assert normalize_category_name("BEVERAGE") == "beverage"
        assert normalize_category_name("Personal Care") == "personal_care"
        assert normalize_category_name("personal-care") == "personal_care"
        assert normalize_category_name("") == ""

    def test_get_available_categories(self):
        categories = get_available_categories()
        assert "food" in categories
        assert "beverage" in categories
        assert "personal_care" in categories
        assert "household" in categories

    def test_load_valid_categories(self):
        for cat in ["food", "beverage", "personal_care", "household"]:
            data = get_rules_for_category(cat)
            assert data["category"] == cat
            assert "rules" in data
            assert len(data["rules"]) > 0
            for r in data["rules"]:
                assert "rule_id" in r
                assert "field" in r
                assert "required" in r
                assert "description" in r
                assert "source" in r

    def test_load_category_case_insensitivity(self):
        data = get_rules_for_category("Food")
        assert data["category"] == "food"

        data_pc = get_rules_for_category("Personal Care")
        assert data_pc["category"] == "personal_care"

    def test_load_missing_category_raises_error(self):
        with pytest.raises(CategoryNotFoundError) as exc_info:
            get_rules_for_category("non_existent_category_xyz")
        assert "non_existent_category_xyz" in str(exc_info.value)
        assert "Available categories" in str(exc_info.value)

    def test_load_empty_category_raises_error(self):
        with pytest.raises(CategoryNotFoundError):
            get_rules_for_category("")

    def test_load_malformed_json_raises_error(self, tmp_path: Path):
        bad_file = tmp_path / "corrupt_category.json"
        bad_file.write_text("{ this is malformed json", encoding="utf-8")

        with pytest.raises(InvalidRuleDefinitionError):
            get_rules_for_category("corrupt_category", definitions_dir=tmp_path)

    def test_load_invalid_schema_structure(self, tmp_path: Path):
        bad_file = tmp_path / "invalid_schema.json"
        bad_file.write_text(json.dumps({"wrong_root": 123}), encoding="utf-8")

        with pytest.raises(InvalidRuleDefinitionError) as exc_info:
            get_rules_for_category("invalid_schema", definitions_dir=tmp_path)
        assert "missing required fields" in str(exc_info.value).lower()
