"""
Legal Compliance Rule Engine for LegalMetrix.

Executes deterministic legal compliance evaluation on structured AI/OCR extracted data.
No LLMs are used in the decision path.

Evaluation Flow:
1. Category Rule Selection (from JSON)
2. Confidence Evaluation & Routing (Per-field)
3. Deterministic Validation (Per-rule)
4. Evidence-backed finding generation
5. Explainable overall compliance status determination
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from rules.engine.applicability import get_rules_for_category
from rules.engine.confidence_router import (
    CONFIDENCE_REVIEW_THRESHOLD,
    route_confidence,
)
from rules.engine.manual_review import create_manual_review_item
from rules.engine.validators import execute_validator


class FindingResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class OverallComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


def _format_evidence(evidence: Any) -> Optional[Any]:
    """
    Normalizes evidence representation without fabricating coordinates.
    """
    if evidence is None:
        return None
    if isinstance(evidence, str):
        return {"frame_id": evidence}
    if isinstance(evidence, dict):
        return evidence
    return {"raw_evidence": str(evidence)}


def evaluate_compliance(
    category: str,
    extracted_data: Optional[Dict[str, Any]] = None,
    confidence_data: Optional[Dict[str, Any]] = None,
    evidence_data: Optional[Dict[str, Any]] = None,
    definitions_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates extracted packaging declarations against deterministic legal rules.

    Args:
        category: Product category (e.g. 'food', 'beverage', 'personal_care', 'household').
        extracted_data: Dict mapping field names to extracted values.
        confidence_data: Dict mapping field names to confidence scores (0-100).
        evidence_data: Dict mapping field names to evidence references (frame, image, region).
        definitions_dir: Optional path override for rule JSON files.

    Returns:
        Dict containing:
            - category: str
            - overall_status: "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_REVIEW"
            - evaluated_at: ISO timestamp
            - summary: Explainable overall summary message
            - findings: List of rule findings with evidence and reasoning
            - manual_reviews: List of fields requiring human review
            - total_rules_evaluated: int
            - passed_count: int
            - failed_count: int
            - uncertain_count: int
    """
    rule_set = get_rules_for_category(category, definitions_dir=definitions_dir)
    rules_list = rule_set.get("rules", [])

    extracted = extracted_data or {}
    confidences = confidence_data or {}
    evidences = evidence_data or {}

    findings: List[Dict[str, Any]] = []
    manual_reviews: List[Dict[str, Any]] = []

    passed_count = 0
    failed_count = 0
    uncertain_count = 0

    for rule in rules_list:
        rule_id = rule.get("rule_id", "UNKNOWN-RULE")
        field = rule.get("field", "")
        required = rule.get("required", True)
        description = rule.get("description", "")
        source = rule.get("source", "")
        rule_version = rule.get("version", "1.0")
        val_config = rule.get("validation")

        val = extracted.get(field)
        conf_val = confidences.get(field)
        ev_val = evidences.get(field)
        formatted_evidence = _format_evidence(ev_val)

        # 1. Determine if extraction has explicit low confidence (< 60%)
        # Low confidence indicates the OCR model attempted to read the field but was uncertain.
        is_low_confidence = False
        if conf_val is not None:
            try:
                is_low_confidence = float(conf_val) < CONFIDENCE_REVIEW_THRESHOLD
            except (ValueError, TypeError):
                is_low_confidence = True

        effective_conf = float(conf_val) if (conf_val is not None and not isinstance(conf_val, str)) else (
            float(conf_val) if isinstance(conf_val, str) and conf_val.replace('.', '', 1).isdigit() else (
                100.0 if val is not None else 100.0
            )
        )
        conf_routing = route_confidence(effective_conf if conf_val is not None else (100.0 if val is not None else 100.0))
        conf_score = conf_routing["confidence"] if conf_val is not None else (100.0 if val is not None else 0.0)

        finding_result: FindingResult
        reason: str

        # 2. If confidence is explicitly below threshold (< 60), route to UNCERTAIN / manual review
        if is_low_confidence:
            finding_result = FindingResult.UNCERTAIN
            reason = (
                f"Extraction confidence ({conf_score:.1f}%) is below minimum threshold "
                f"({CONFIDENCE_REVIEW_THRESHOLD}%). Manual officer verification required before legal evaluation."
            )
            uncertain_count += 1

            review_item = create_manual_review_item(
                field=field,
                ai_value=val,
                confidence=conf_score,
                reason=reason,
                evidence=formatted_evidence,
                rule_id=rule_id,
            )
            manual_reviews.append(review_item)

        else:
            # 3. Deterministic validation
            is_valid, val_reason = execute_validator(val_config, val)
            if is_valid:
                finding_result = FindingResult.PASS
                reason = val_reason
                passed_count += 1
            else:
                finding_result = FindingResult.FAIL
                reason = val_reason
                failed_count += 1

        findings.append({
            "rule_id": rule_id,
            "rule_version": rule_version,
            "field": field,
            "required": required,
            "requirement": description,
            "result": finding_result.value,
            "reason": reason,
            "extracted_value": val,
            "confidence": conf_score,
            "confidence_tier": conf_routing["tier"],
            "evidence": formatted_evidence,
            "source": source,
        })

    # 4. Overall status determination
    # Strict separation: Deterministic failure -> NON_COMPLIANT.
    # No failure but uncertainty -> NEEDS_REVIEW.
    # All passed with reliable confidence -> COMPLIANT.
    if failed_count > 0:
        overall_status = OverallComplianceStatus.NON_COMPLIANT
        summary = (
            f"Non-compliance detected: {failed_count} mandatory declaration(s) failed deterministic legal validation."
        )
    elif uncertain_count > 0:
        overall_status = OverallComplianceStatus.NEEDS_REVIEW
        summary = (
            f"Officer review required: {uncertain_count} declaration(s) have low extraction confidence and require verification."
        )
    else:
        overall_status = OverallComplianceStatus.COMPLIANT
        summary = (
            f"Compliant: All {passed_count} evaluated mandatory declaration(s) satisfy legal requirements."
        )

    return {
        "category": category,
        "definition_version": rule_set.get("version", "1.0"),
        "overall_status": overall_status.value,
        "summary": summary,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_rules_evaluated": len(rules_list),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "uncertain_count": uncertain_count,
        "findings": findings,
        "manual_reviews": manual_reviews,
    }
