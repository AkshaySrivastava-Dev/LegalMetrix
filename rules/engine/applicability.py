"""
Category Rule Selection & Applicability Loader for LegalMetrix.

Safely loads category-specific rule definitions from JSON files.
Ensures zero silent fallbacks and deterministic error handling.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class RuleEngineException(Exception):
    """Base exception for LegalMetrix Rule Engine."""
    pass


class CategoryNotFoundError(RuleEngineException):
    """Raised when the requested product category rule definition does not exist."""
    pass


class InvalidRuleDefinitionError(RuleEngineException):
    """Raised when a rule definition file is malformed or invalid."""
    pass


# Default path to definitions directory
DEFAULT_DEFINITIONS_DIR = Path(__file__).resolve().parent.parent / "definitions"


def normalize_category_name(category: str) -> str:
    """
    Normalizes category string to standard filename key format.
    e.g. 'Food' -> 'food', 'Personal Care' -> 'personal_care'
    """
    if not category:
        return ""
    return category.strip().lower().replace(" ", "_").replace("-", "_")


def get_available_categories(definitions_dir: Optional[Path] = None) -> List[str]:
    """
    Returns list of available category identifiers based on JSON definition files.
    """
    base_dir = definitions_dir or DEFAULT_DEFINITIONS_DIR
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    
    categories = []
    for file_path in base_dir.glob("*.json"):
        categories.append(file_path.stem)
    return sorted(categories)


def get_rules_for_category(
    category: str,
    definitions_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Loads rule definition set for the given product category.

    Args:
        category: Category name (e.g. 'food', 'beverage', 'personal_care', 'household')
        definitions_dir: Optional directory override for rule JSON files.

    Returns:
        Dict containing category, version, description, and list of rule dictionaries.

    Raises:
        CategoryNotFoundError: If no definition file exists for the category.
        InvalidRuleDefinitionError: If definition file is unreadable or malformed JSON.
    """
    if not category or not isinstance(category, str) or not category.strip():
        raise CategoryNotFoundError(f"Category name cannot be empty. Received: '{category}'")

    normalized_cat = normalize_category_name(category)
    base_dir = definitions_dir or DEFAULT_DEFINITIONS_DIR
    rule_file = base_dir / f"{normalized_cat}.json"

    if not rule_file.exists():
        available = get_available_categories(base_dir)
        raise CategoryNotFoundError(
            f"No rule definition found for category '{category}' (normalized: '{normalized_cat}'). "
            f"Available categories: {available}"
        )

    try:
        with open(rule_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise InvalidRuleDefinitionError(
            f"Rule definition file '{rule_file.name}' contains invalid JSON: {e}"
        ) from e
    except Exception as e:
        raise InvalidRuleDefinitionError(
            f"Could not read rule definition file '{rule_file.name}': {e}"
        ) from e

    # Structural sanity check
    if not isinstance(data, dict):
        raise InvalidRuleDefinitionError(
            f"Rule definition file '{rule_file.name}' must contain a JSON object at root."
        )

    if "category" not in data or "rules" not in data or not isinstance(data["rules"], list):
        raise InvalidRuleDefinitionError(
            f"Rule definition file '{rule_file.name}' is missing required fields 'category' or 'rules'."
        )

    return data
