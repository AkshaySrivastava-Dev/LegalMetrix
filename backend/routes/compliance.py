"""
Compliance Routes.
Direct endpoint (POST /api/compliance) to evaluate product declarations without uploading a new image.
"""

import logging
from fastapi import APIRouter, status
from ..models.schemas import ComplianceRequest, ComplianceResult
from ..services.compliance_service import check_compliance

logger = logging.getLogger("legal_metrology.routes.compliance")
router = APIRouter(prefix="/api", tags=["Compliance Engine"])


@router.post(
    "/compliance",
    response_model=ComplianceResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Legal Metrology Compliance",
    description="Validates product metadata (MRP, Net Qty, Manufacturer, etc.) against Legal Metrology Rules, 2011.",
)
async def evaluate_compliance(request: ComplianceRequest):
    """
    Accepts extracted product parameters directly and returns rule compliance status,
    confidence score, check statuses, and violations.
    """
    logger.info(f"Direct compliance check requested for product: '{request.product_name}' (Brand: '{request.brand}')")
    result = check_compliance(request)
    return result
