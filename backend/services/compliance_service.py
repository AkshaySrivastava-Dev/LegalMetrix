"""
Compliance Service Adapter.
Acts strictly as an integration wrapper/adapter for the Compliance Module.
Does NOT implement or duplicate the Legal Metrology rule engine.
When MOCK_COMPLIANCE=true, returns realistic mock compliance outputs for demo/development.
"""

import os
import logging
from typing import Dict, Any, Union, List
from ..models.schemas import (
    ComplianceResult,
    ComplianceCheck,
    ComplianceViolation,
    AIAnalysisResult,
    ComplianceRequest,
)

logger = logging.getLogger("legal_metrology.compliance_service")


def is_mock_compliance_enabled() -> bool:
    """Returns True if mock compliance mode is enabled via environment variables."""
    return os.getenv("MOCK_COMPLIANCE", "true").strip().lower() in ("true", "1", "yes")


def check_compliance(
    data: Union[AIAnalysisResult, ComplianceRequest, Dict[str, Any]]
) -> ComplianceResult:
    """
    Adapter function to evaluate Legal Metrology compliance.
    Delegates to the external compliance engine when integrated, or provides a clean mock fallback.
    """
    logger.info(f"Compliance Adapter: check_compliance called (mock_mode={is_mock_compliance_enabled()})")

    # Normalize input into standard dictionary
    if isinstance(data, (AIAnalysisResult, ComplianceRequest)):
        payload = data.model_dump()
    elif isinstance(data, dict):
        payload = data
    else:
        payload = {}

    # 1. External Module Integration Hook
    if not is_mock_compliance_enabled():
        try:
            # Future integration hook:
            # from compliance_module import evaluate_compliance_rules
            # res = evaluate_compliance_rules(payload)
            # return ComplianceResult(**res)
            pass
        except Exception as e:
            logger.error(f"External Compliance module failed: {e}. Falling back to adapter mock.")

    # 2. Clean Mock Implementation (Demo / Prototype Mode)
    # Simple check for mock demonstration purposes:
    has_mrp = bool(payload.get("mrp"))
    has_qty = bool(payload.get("net_quantity"))
    has_name = bool(payload.get("product_name"))

    if has_mrp and has_qty and has_name:
        # Realistic sample mock compliant response
        return ComplianceResult(
            compliance_status="COMPLIANT",
            confidence=0.95,
            checks=[
                ComplianceCheck(
                    field="product_name",
                    rule="Rule 6(1)(a) - Name / Generic Identity",
                    passed=True,
                    detected_value=str(payload.get("product_name")),
                    message="Product identity clearly declared.",
                ),
                ComplianceCheck(
                    field="net_quantity",
                    rule="Rule 6(1)(d) - Net Quantity Declaration",
                    passed=True,
                    detected_value=str(payload.get("net_quantity")),
                    message="Net quantity format is compliant.",
                ),
                ComplianceCheck(
                    field="mrp",
                    rule="Rule 6(1)(e) - Maximum Retail Price",
                    passed=True,
                    detected_value=str(payload.get("mrp")),
                    message="MRP declared with inclusive of all taxes.",
                ),
                ComplianceCheck(
                    field="manufacturer",
                    rule="Rule 6(1)(a) - Manufacturer / Packer Address",
                    passed=True,
                    detected_value=str(payload.get("manufacturer") or "Declared on package"),
                    message="Manufacturer/Packer details present.",
                ),
            ],
            violations=[],
            summary="[MOCK COMPLIANCE] All mandatory Legal Metrology declarations verified successfully.",
        )
    else:
        # Realistic sample mock non-compliant response
        violations = []
        if not has_name:
            violations.append(
                ComplianceViolation(
                    field="product_name",
                    rule="Rule 6(1)(a) - Generic Identity",
                    severity="high",
                    issue="Commodity name absent or unreadable.",
                    suggestion="Declare generic commodity name on principal display panel.",
                )
            )
        if not has_qty:
            violations.append(
                ComplianceViolation(
                    field="net_quantity",
                    rule="Rule 6(1)(d) - Net Quantity Declaration",
                    severity="high",
                    issue="Mandatory Net Quantity declaration missing.",
                    suggestion="Declare net weight/volume in standard metric units.",
                )
            )
        if not has_mrp:
            violations.append(
                ComplianceViolation(
                    field="mrp",
                    rule="Rule 6(1)(e) - Maximum Retail Price",
                    severity="high",
                    issue="Mandatory Maximum Retail Price (MRP) missing.",
                    suggestion="Clearly display MRP inclusive of all taxes.",
                )
            )

        return ComplianceResult(
            compliance_status="NON_COMPLIANT",
            confidence=0.90,
            checks=[
                ComplianceCheck(
                    field="product_name",
                    rule="Rule 6(1)(a) - Generic Identity",
                    passed=has_name,
                    detected_value=str(payload.get("product_name")) if has_name else None,
                    message="Product name check.",
                ),
                ComplianceCheck(
                    field="net_quantity",
                    rule="Rule 6(1)(d) - Net Quantity Declaration",
                    passed=has_qty,
                    detected_value=str(payload.get("net_quantity")) if has_qty else None,
                    message="Net quantity check.",
                ),
                ComplianceCheck(
                    field="mrp",
                    rule="Rule 6(1)(e) - Maximum Retail Price",
                    passed=has_mrp,
                    detected_value=str(payload.get("mrp")) if has_mrp else None,
                    message="MRP check.",
                ),
            ],
            violations=violations,
            summary=f"[MOCK COMPLIANCE] {len(violations)} mandatory declaration violation(s) detected.",
        )
