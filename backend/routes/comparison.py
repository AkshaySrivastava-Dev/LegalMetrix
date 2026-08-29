"""
Physical vs Online Comparison Routes.
Provides endpoint (POST /api/comparison) to verify physical pack declarations against controlled online benchmarks.
"""

import logging
from fastapi import APIRouter, status
from ..models.schemas import ComparisonRequest, ComparisonResponse
from ..services.comparison_service import compare_product
from ..services.database_service import get_inspection
from ..utils.errors import NotFoundException

logger = logging.getLogger("legal_metrology.routes.comparison")
router = APIRouter(prefix="/api", tags=["Physical vs Online Comparison"])


@router.post(
    "/comparison",
    response_model=ComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Physical Packaging with Online Benchmark",
    description="Compares physical product declarations (or saved inspection) with controlled online reference catalog data to detect discrepancies.",
)
async def compare_physical_and_online(request: ComparisonRequest):
    """
    Accepts physical data directly or looks up an existing inspection_id,
    then executes field comparison against controlled online benchmark data.
    """
    payload = request.model_dump(exclude_unset=True)

    # If inspection_id was specified, load details from database if physical fields were omitted
    if request.inspection_id:
        existing = get_inspection(request.inspection_id)
        if not existing:
            raise NotFoundException(f"Inspection record '{request.inspection_id}' not found for comparison.")
        # Merge existing DB values as fallback for missing request fields
        for k in ("product_name", "brand", "category", "variant", "mrp", "net_quantity", "manufacturer"):
            if not payload.get(k) and existing.get(k):
                payload[k] = existing.get(k)

    result = compare_product(payload)
    return result
