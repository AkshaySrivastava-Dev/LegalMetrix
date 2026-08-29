"""
Deterministic Validators for LegalMetrix Rule Engine.

Executes deterministic validation checks (presence, exact, pattern, numeric, range)
without legal interpretations. Keeps logic purely computational and explainable.
"""

import re
from typing import Any, Dict, Optional, Tuple, Union


def validate_presence(value: Any) -> bool:
    """
    Validates whether a value is present and non-empty.

    Returns False for:
        - None
        - empty string
        - whitespace-only string
        - empty list / dict / set

    Returns True for:
        - non-empty strings, numbers (including 0), booleans, populated structures.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return len(value.strip()) > 0
    if isinstance(value, (list, dict, set, tuple)):
        return len(value) > 0
    return True


def validate_exact(value: Any, expected: Any, case_sensitive: bool = False) -> bool:
    """
    Validates if value exactly matches expected value.
    """
    if not validate_presence(value) or not validate_presence(expected):
        return False
    if isinstance(value, str) and isinstance(expected, str):
        if not case_sensitive:
            return value.strip().lower() == expected.strip().lower()
        return value.strip() == expected.strip()
    return value == expected


def validate_pattern(value: Any, pattern: str) -> bool:
    """
    Validates if string representation of value matches regular expression pattern.
    """
    if not validate_presence(value) or not pattern:
        return False
    try:
        return re.search(pattern, str(value).strip()) is not None
    except re.error:
        return False


def _extract_numeric_value(value: Any) -> Optional[float]:
    """
    Safely extracts a numeric float value from a number or string.
    Handles currency symbols and units if simple.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        # Remove common currency and whitespace prefix/suffixes if standard
        cleaned = re.sub(r'^[₹$€£\s]*', '', cleaned)
        cleaned = re.sub(r'^(rs\.?|inr)\s*', '', cleaned, flags=re.IGNORECASE)
        # Extract first valid floating point number
        match = re.search(r'[-+]?\d*\.?\d+', cleaned)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
    return None


def validate_numeric(
    value: Any,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
) -> bool:
    """
    Validates whether the value is numeric and within optional bounds.
    """
    num = _extract_numeric_value(value)
    if num is None:
        return False
    if min_value is not None and num < min_value:
        return False
    if max_value is not None and num > max_value:
        return False
    return True


def validate_range(
    value: Any,
    min_value: Union[int, float],
    max_value: Union[int, float],
) -> bool:
    """
    Validates whether value falls within numeric range [min_value, max_value].
    """
    return validate_numeric(value, min_value=min_value, max_value=max_value)


def execute_validator(
    validation_config: Optional[Dict[str, Any]],
    value: Any,
) -> Tuple[bool, str]:
    """
    Dispatches validation based on validation_config dict.

    Returns:
        (is_valid: bool, reason: str)
    """
    if not validation_config:
        # Default fallback to presence check if no specific config provided
        is_present = validate_presence(value)
        return (is_present, "Field presence verified" if is_present else "Required field is missing or empty")

    val_type = validation_config.get("type", "presence")

    if val_type == "presence":
        if validate_presence(value):
            return (True, "Required declaration is present")
        return (False, "Required declaration is missing or unreadable")

    elif val_type == "exact":
        expected = validation_config.get("expected_value")
        case_sens = validation_config.get("case_sensitive", False)
        if validate_exact(value, expected, case_sens):
            return (True, f"Field matches expected value '{expected}'")
        return (False, f"Field value '{value}' does not match expected '{expected}'")

    elif val_type == "pattern":
        pattern = validation_config.get("pattern", "")
        if validate_pattern(value, pattern):
            return (True, f"Field satisfies format pattern '{pattern}'")
        return (False, f"Field value '{value}' does not match required pattern '{pattern}'")

    elif val_type == "numeric":
        min_v = validation_config.get("min_value")
        max_v = validation_config.get("max_value")
        if validate_numeric(value, min_value=min_v, max_value=max_v):
            return (True, "Field is a valid numeric value within constraints")
        return (False, f"Field value '{value}' is not a valid number within specified limits")

    elif val_type == "range":
        min_v = validation_config.get("min_value")
        max_v = validation_config.get("max_value")
        if min_v is None or max_v is None:
            return (False, "Range validator configuration missing min_value or max_value")
        if validate_range(value, min_v, max_v):
            return (True, f"Numeric value is within range [{min_v}, {max_v}]")
        return (False, f"Numeric value '{value}' is outside permitted range [{min_v}, {max_v}]")

    else:
        # Unsupported validation type
        return (False, f"Unsupported validation type '{val_type}' in rule configuration")
