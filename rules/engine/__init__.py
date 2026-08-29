"""
LegalMetrix Legal Rule Engine Module.
"""

from rules.engine.applicability import (
    CategoryNotFoundError,
    InvalidRuleDefinitionError,
    get_available_categories,
    get_rules_for_category,
)
from rules.engine.confidence_router import (
    CONFIDENCE_AUTO_THRESHOLD,
    CONFIDENCE_REVIEW_THRESHOLD,
    ConfidenceTier,
    route_confidence,
)
from rules.engine.manual_review import (
    ReviewAction,
    ReviewStatus,
    apply_manual_review,
    create_manual_review_item,
)
from rules.engine.rule_engine import (
    FindingResult,
    OverallComplianceStatus,
    evaluate_compliance,
)
from rules.engine.validators import (
    execute_validator,
    validate_exact,
    validate_numeric,
    validate_pattern,
    validate_presence,
    validate_range,
)

__all__ = [
    "get_rules_for_category",
    "get_available_categories",
    "CategoryNotFoundError",
    "InvalidRuleDefinitionError",
    "route_confidence",
    "ConfidenceTier",
    "CONFIDENCE_AUTO_THRESHOLD",
    "CONFIDENCE_REVIEW_THRESHOLD",
    "evaluate_compliance",
    "FindingResult",
    "OverallComplianceStatus",
    "create_manual_review_item",
    "apply_manual_review",
    "ReviewAction",
    "ReviewStatus",
    "validate_presence",
    "validate_exact",
    "validate_pattern",
    "validate_numeric",
    "validate_range",
    "execute_validator",
]
