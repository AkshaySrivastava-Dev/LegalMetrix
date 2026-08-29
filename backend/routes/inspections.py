"""
Inspections History Routes.
Provides endpoints to fetch single inspections, paginated history, and same-product lookups.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, status
from ..models.schemas import InspectionResponse, InspectionListResponse
from ..services.database_service import get_inspection, get_inspections, get_same_product
from ..utils.errors import NotFoundException

logger = logging.getLogger("legal_metrology.routes.inspections")
router = APIRouter(prefix="/api", tags=["Inspection History"])


@router.get(
    "/inspections/same-product",
    response_model=List[InspectionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Past Inspections for Same Product",
    description="Look up previous inspection records matching brand, product name, category, or variant.",
)
async def get_inspections_same_product(
    brand: Optional[str] = Query(None, description="Brand name to match"),
    product_name: Optional[str] = Query(None, description="Product / commodity name to match"),
    category: Optional[str] = Query(None, description="Commodity category"),
    variant: Optional[str] = Query(None, description="Variant"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
):
    """Retrieves previous inspections for identical or related products."""
    records = get_same_product(
        brand=brand,
        product_name=product_name,
        category=category,
        variant=variant,
        limit=limit,
    )
    return [InspectionResponse(**r) for r in records]


@router.get(
    "/inspection/{inspection_id}",
    response_model=InspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Inspection Details by ID",
    description="Retrieve a complete saved inspection record including AI detections, checks, and violations.",
)
async def get_single_inspection(inspection_id: str):
    """Fetches an inspection record by its unique ID."""
    record = get_inspection(inspection_id)
    if not record:
        raise NotFoundException(f"Inspection record with ID '{inspection_id}' was not found.")
    return InspectionResponse(**record)


@router.get(
    "/inspections",
    response_model=InspectionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Inspection History",
    description="Retrieve paginated inspection history with optional status filters.",
)
async def list_inspections(
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    compliance_status: Optional[str] = Query(None, description="Filter by status (COMPLIANT, NON_COMPLIANT, PARTIALLY_COMPLIANT)"),
    sync_status: Optional[str] = Query(None, description="Filter by sync status (synced, pending, failed)"),
):
    """Returns a list of inspections with pagination metadata."""
    items, total = get_inspections(
        limit=limit,
        offset=offset,
        compliance_status=compliance_status,
        sync_status=sync_status,
    )
    return InspectionListResponse(
        total=total,
        items=[InspectionResponse(**item) for item in items],
    )
