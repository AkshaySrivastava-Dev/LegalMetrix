"""
Manual Review Module for LegalMetrix.

Handles officer human-in-the-loop verification for low-confidence AI extractions.
Supports:
- CONFIRM: Officer verifies AI extraction is correct
- CORRECT: Officer inputs correct declaration while strictly preserving AI original
- MARK_UNREADABLE: Officer confirms label is unreadable on the physical package
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ReviewAction(str, Enum):
    CONFIRM = "CONFIRM"
    CORRECT = "CORRECT"
    MARK_UNREADABLE = "MARK_UNREADABLE"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


def create_manual_review_item(
    field: str,
    ai_value: Any,
    confidence: float,
    reason: str,
    evidence: Optional[Any] = None,
    rule_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a pending manual review item for an uncertain extraction.

    Args:
        field: Name of the extracted field.
        ai_value: Value extracted by AI/OCR.
        confidence: Extraction confidence score.
        reason: Explanation for why review is required.
        evidence: Evidence reference (frame_id, image_id, bounding box).
        rule_id: Associated legal rule ID if applicable.

    Returns:
        Dict representing the pending review entry.
    """
    return {
        "field": field,
        "rule_id": rule_id,
        "ai_value": ai_value,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
        "status": ReviewStatus.PENDING.value,
        "requires_manual_review": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "action": None,
        "corrected_value": None,
        "reviewer_id": None,
        "notes": None,
    }


def apply_manual_review(
    review_item: Dict[str, Any],
    action: Union[str, ReviewAction],
    reviewer_id: str,
    corrected_value: Optional[Any] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Applies an officer review decision to a review item.
    Guarantees that original AI value, confidence, and evidence are preserved.

    Args:
        review_item: The existing review item dictionary.
        action: "CONFIRM", "CORRECT", or "MARK_UNREADABLE".
        reviewer_id: Officer identifier.
        corrected_value: New value supplied if action is CORRECT.
        notes: Optional officer observations.

    Returns:
        Updated review item dictionary with preserved audit trail.
    """
    if isinstance(action, str):
        try:
            act_enum = ReviewAction(action.upper())
        except ValueError:
            raise ValueError(f"Invalid review action '{action}'. Permitted: {[a.value for a in ReviewAction]}")
    else:
        act_enum = action

    updated = dict(review_item)
    updated["status"] = ReviewStatus.COMPLETED.value
    updated["action"] = act_enum.value
    updated["reviewer_id"] = reviewer_id
    updated["resolved_at"] = datetime.now(timezone.utc).isoformat()
    updated["notes"] = notes

    if act_enum == ReviewAction.CORRECT:
        if corrected_value is None:
            raise ValueError("corrected_value must be provided when action is CORRECT")
        updated["corrected_value"] = corrected_value
        updated["effective_value"] = corrected_value
    elif act_enum == ReviewAction.CONFIRM:
        updated["effective_value"] = updated.get("ai_value")
        updated["corrected_value"] = None
    elif act_enum == ReviewAction.MARK_UNREADABLE:
        updated["effective_value"] = None
        updated["corrected_value"] = None

    return updated
