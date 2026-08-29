"""
Scan Routes.
Handles single photo scans (POST /api/scan) and 360-degree video scans (POST /api/scan/360).
Orchestrates: File Validation -> AI Analysis -> Compliance Checking -> Database Persistence.
"""

import logging
from fastapi import APIRouter, UploadFile, File, status
from ..models.schemas import InspectionResponse
from ..utils.files import save_upload_file
from ..services.ai_service import analyze_image, analyze_video
from ..services.compliance_service import check_compliance
from ..services.database_service import save_inspection

logger = logging.getLogger("legal_metrology.routes.scan")
router = APIRouter(prefix="/api", tags=["Scanning & Ingestion"])


@router.post(
    "/scan",
    response_model=InspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan Packaged Commodity Image",
    description="Upload a photo of packaged commodity packaging to extract declarations, check compliance, and save to inspection history.",
)
async def scan_image(image: UploadFile = File(...)):
    """
    Receives image upload, validates, extracts text/fields via AI service,
    evaluates Legal Metrology rules, records in DB, and returns structured result.
    """
    logger.info(f"Received photo upload: {image.filename} ({image.content_type})")

    # 1. Validate and save image locally
    saved_file_path = await save_upload_file(image, is_video=False)

    # 2. Extract product details via AI / OCR adapter
    ai_result = await analyze_image(saved_file_path)

    # 3. Evaluate Legal Metrology compliance
    compliance_result = check_compliance(ai_result)

    # 4. Consolidate into persistent inspection record
    inspection_payload = {
        "product_name": ai_result.product_name,
        "brand": ai_result.brand,
        "category": ai_result.category,
        "variant": ai_result.variant,
        "mrp": ai_result.mrp,
        "net_quantity": ai_result.net_quantity,
        "manufacturer": ai_result.manufacturer,
        "confidence": (ai_result.confidence + compliance_result.confidence) / 2.0,
        "compliance_status": compliance_result.compliance_status,
        "violations": [v.model_dump() for v in compliance_result.violations],
        "checks": [c.model_dump() for c in compliance_result.checks],
        "evidence": ai_result.evidence or {},
        "source": "image",
        "file_path": saved_file_path,
        "sync_status": "synced",
    }

    # 5. Persist to database
    saved_record = save_inspection(inspection_payload)
    logger.info(f"Inspection completed successfully: ID={saved_record.get('inspection_id')} status={saved_record.get('compliance_status')}")

    return InspectionResponse(**saved_record)


@router.post(
    "/scan/360",
    response_model=InspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan 360-degree Commodity Video",
    description="Upload a short continuous rotation video of a package to analyze multiple panels, aggregate text, and verify compliance.",
)
async def scan_video(video: UploadFile = File(...)):
    """
    Receives 360 video upload, validates, aggregates multi-angle frames via AI service,
    evaluates Legal Metrology compliance, and records in DB.
    """
    logger.info(f"Received 360 video upload: {video.filename} ({video.content_type})")

    # 1. Validate and save video
    saved_video_path = await save_upload_file(video, is_video=True)

    # 2. Extract product details across frames via AI adapter
    ai_result = await analyze_video(saved_video_path)

    # 3. Evaluate Legal Metrology compliance
    compliance_result = check_compliance(ai_result)

    # 4. Consolidate into persistent inspection record
    inspection_payload = {
        "product_name": ai_result.product_name,
        "brand": ai_result.brand,
        "category": ai_result.category,
        "variant": ai_result.variant,
        "mrp": ai_result.mrp,
        "net_quantity": ai_result.net_quantity,
        "manufacturer": ai_result.manufacturer,
        "confidence": (ai_result.confidence + compliance_result.confidence) / 2.0,
        "compliance_status": compliance_result.compliance_status,
        "violations": [v.model_dump() for v in compliance_result.violations],
        "checks": [c.model_dump() for c in compliance_result.checks],
        "evidence": ai_result.evidence or {},
        "source": "video_360",
        "file_path": saved_video_path,
        "sync_status": "synced",
    }

    # 5. Persist to database
    saved_record = save_inspection(inspection_payload)
    logger.info(f"360 Video Inspection completed: ID={saved_record.get('inspection_id')}")

    return InspectionResponse(**saved_record)
