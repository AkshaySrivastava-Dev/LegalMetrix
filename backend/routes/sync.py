"""
Offline Sync Routes.
Enables field officers to sync offline-captured inspections when internet connectivity is restored.
Handles batch processing, duplicate IDs, and idempotent database updates.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from ..services.database_service import process_sync_batch

logger = logging.getLogger("legal_metrology.routes.sync")
router = APIRouter(prefix="/api", tags=["Offline Synchronization"])


class SyncRecordItem(BaseModel):
    inspection_id: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    variant: Optional[str] = None
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence: Optional[float] = 0.0
    compliance_status: Optional[str] = "UNKNOWN"
    violations: Optional[List[Any]] = Field(default_factory=list)
    checks: Optional[List[Any]] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: Optional[str] = "image"
    file_path: Optional[str] = None
    created_at: Optional[str] = None
    sync_status: Optional[str] = "synced"


class SyncRequest(BaseModel):
    records: List[SyncRecordItem] = Field(default_factory=list)


class SyncResultItem(BaseModel):
    inspection_id: str
    status: str
    action: Optional[str] = None
    reason: Optional[str] = None


class SyncResponse(BaseModel):
    total_received: int
    synced_count: int
    failed_count: int
    results: List[SyncResultItem]


@router.post(
    "/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Offline Inspection Records",
    description="Accepts a batch of offline inspection records collected on mobile devices and syncs them safely to the central database.",
)
async def sync_offline_records(request: SyncRequest):
    """
    Processes batch sync records.
    Safely handles existing/duplicate records, creates missing records, and returns detailed status for each item.
    """
    logger.info(f"Sync request received with {len(request.records)} record(s).")
    raw_records = [record.model_dump() for record in request.records]
    result_data = process_sync_batch(raw_records)

    return SyncResponse(
        total_received=result_data["total_received"],
        synced_count=result_data["synced_count"],
        failed_count=result_data["failed_count"],
        results=[SyncResultItem(**r) for r in result_data["results"]],
    )
