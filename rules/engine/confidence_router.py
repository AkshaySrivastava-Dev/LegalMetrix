"""
Confidence Routing Module for LegalMetrix.

Routes AI/OCR confidence scores to appropriate operational tiers:
- >= 90: AUTO (High confidence, automated processing permitted)
- 60 - 89: REVIEW_RECOMMENDED (Moderate confidence, flagged for optional review)
- < 60: MANUAL_VERIFICATION (Low confidence, requires mandatory manual officer verification)

Critical Principle:
Confidence represents extraction certainty, NOT legal compliance.
Low confidence must NOT be converted to a legal violation.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union


class ConfidenceTier(str, Enum):
    AUTO = "AUTO"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    MANUAL_VERIFICATION = "MANUAL_VERIFICATION"


# Configurable threshold constants
CONFIDENCE_AUTO_THRESHOLD = 90.0
CONFIDENCE_REVIEW_THRESHOLD = 60.0


def route_confidence(confidence: Optional[Union[int, float, Any]]) -> Dict[str, Any]:
    """
    Evaluates extraction confidence score and returns routing metadata.

    Args:
        confidence: Numeric confidence score (typically 0 - 100).

    Returns:
        Dict containing:
            - tier: ConfidenceTier ("AUTO", "REVIEW_RECOMMENDED", "MANUAL_VERIFICATION")
            - requires_manual_review: bool (True if < 60 or missing)
            - review_recommended: bool (True if 60 <= conf < 90)
            - confidence: float (sanitized value)
            - explanation: str
    """
    if confidence is None:
        return {
            "tier": ConfidenceTier.MANUAL_VERIFICATION.value,
            "requires_manual_review": True,
            "review_recommended": True,
            "confidence": 0.0,
            "explanation": "Confidence score is missing; mandatory manual verification required.",
        }

    try:
        conf_float = float(confidence)
    except (ValueError, TypeError):
        return {
            "tier": ConfidenceTier.MANUAL_VERIFICATION.value,
            "requires_manual_review": True,
            "review_recommended": True,
            "confidence": 0.0,
            "explanation": f"Invalid confidence value '{confidence}'; mandatory manual verification required.",
        }

    # Normalize bounded value [0, 100]
    conf_clamped = max(0.0, min(100.0, conf_float))

    if conf_clamped >= CONFIDENCE_AUTO_THRESHOLD:
        return {
            "tier": ConfidenceTier.AUTO.value,
            "requires_manual_review": False,
            "review_recommended": False,
            "confidence": conf_clamped,
            "explanation": f"High confidence ({conf_clamped:.1f}%) meets threshold for automated verification.",
        }
    elif conf_clamped >= CONFIDENCE_REVIEW_THRESHOLD:
        return {
            "tier": ConfidenceTier.REVIEW_RECOMMENDED.value,
            "requires_manual_review": False,
            "review_recommended": True,
            "confidence": conf_clamped,
            "explanation": f"Moderate confidence ({conf_clamped:.1f}%) warrants optional officer review.",
        }
    else:
        return {
            "tier": ConfidenceTier.MANUAL_VERIFICATION.value,
            "requires_manual_review": True,
            "review_recommended": True,
            "confidence": conf_clamped,
            "explanation": f"Low extraction confidence ({conf_clamped:.1f}% < {CONFIDENCE_REVIEW_THRESHOLD}%) requires mandatory officer verification.",
        }
