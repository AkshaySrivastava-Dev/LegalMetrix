"""
FastAPI Route Handlers for LegalMetrix AI-Assisted Legal Metrology Inspection System.

Orchestrates:
  Image / 360 Video Ingestion
  -> AI/OCR Pipeline & Multi-Image Fusion
  -> Field Extraction & Confidence Mapping
  -> Category Resolution
  -> Deterministic Legal Metrology Rule Evaluation
  -> Evidence & Inspection Persistence (SQLite)
  -> Offline Batch Synchronization & History Tracking
  -> Physical vs Online Catalog Reconciliation
"""

import os
import cv2
import json
import logging
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import APIRouter, File, Form, HTTPException, Path as FPath, Query, UploadFile, status

from api.schemas import (
    CategoryRulesResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComplianceEvaluationRequest,
    ComplianceEvaluationResponse,
    DemoScenarioItem,
    HealthResponse,
    HistoricalComparisonRequest,
    HistoricalComparisonResponse,
    InspectionListResponse,
    InspectionResponse,
    ManualReviewResultResponse,
    ManualReviewSubmission,
    ReconciliationRequest,
    ReconciliationResponse,
    SyncItem,
    SyncRequest,
    SyncResponse,
    SyncResultItem,
)
from api.storage import db, get_db_path
from reconciliation.comparator import (
    compare_historical,
    compare_product,
    find_previous_inspections,
)
from rules.engine import (
    CategoryNotFoundError,
    InvalidRuleDefinitionError,
    apply_manual_review,
    create_manual_review_item,
    evaluate_compliance,
    get_rules_for_category,
)
from utils.files import get_upload_base_dir, save_upload_file
from utils.errors import NotFoundException, ValidationException

logger = logging.getLogger("legalmetrix.routes")
router = APIRouter(prefix="/api", tags=["LegalMetrix"])

_ai_pipeline = None
_multi_image_fusion = None


def get_ai_pipeline():
    """Lazy loader for InspectionAI pipeline."""
    global _ai_pipeline
    if _ai_pipeline is None:
        from ai.pipeline import InspectionAI
        _ai_pipeline = InspectionAI(save_evidence=False)
    return _ai_pipeline


def get_multi_image_fusion():
    """Lazy loader for MultiImageFusion module."""
    global _multi_image_fusion
    if _multi_image_fusion is None:
        from ai.multi_image import MultiImageFusion
        _multi_image_fusion = MultiImageFusion()
    return _multi_image_fusion


def map_ai_fields_to_compliance(
    ai_fields: Dict[str, Any],
    source_name: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, Any]]:
    """Maps fields output from ai.field_extractor to LegalMetrix compliance evaluation format."""
    extracted: Dict[str, Any] = {}
    confidences: Dict[str, float] = {}
    evidences: Dict[str, Any] = {}

    field_keys = {
        "product_name": ["product_name"],
        "brand": ["brand"],
        "mrp": ["mrp"],
        "net_quantity": ["net_quantity"],
        "manufacturer": ["manufacturer", "packer", "importer"],
        "country_of_origin": ["country_of_origin"],
        "date_of_manufacture": ["manufacturing_date", "date_of_manufacture"],
        "expiry_date": ["expiry_date"],
        "batch_number": ["batch_number"],
        "consumer_care": ["consumer_care", "customer_care"],
    }

    for target_key, candidate_keys in field_keys.items():
        for cand in candidate_keys:
            field_obj = ai_fields.get(cand)
            if field_obj and isinstance(field_obj, dict):
                val = field_obj.get("value")
                if val is not None:
                    extracted[target_key] = val
                    conf = _normalize_confidence_score(field_obj.get("confidence"))
                    if conf is not None:
                        confidences[target_key] = conf
                    box = field_obj.get("box")
                    evidences[target_key] = {
                        "frame_id": source_name or "uploaded_image",
                        "box": box,
                    }
                    break

    for k, v in ai_fields.items():
        if k not in field_keys and k not in extracted and isinstance(v, dict):
            val = v.get("value")
            if val is not None:
                extracted[k] = val
                conf = _normalize_confidence_score(v.get("confidence"))
                if conf is not None:
                    confidences[k] = conf
                evidences[k] = {
                    "frame_id": source_name or "uploaded_image",
                    "box": v.get("box"),
                }

    return extracted, confidences, evidences


def _normalize_confidence_score(val: Any) -> Optional[float]:
    """Normalizes confidence scores whether provided as 0.0-1.0 or 0-100."""
    if val is None:
        return None
    try:
        f = float(val)
        if 0.0 < f <= 1.0:
            return round(f * 100.0, 2)
        return round(f, 2)
    except (ValueError, TypeError):
        return None


# ------------------ System Health Check Endpoint ------------------ #
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Status Check",
    tags=["System"],
)
def get_system_health():
    """Returns runtime health, storage status, and active database connection."""
    db_status = "connected"
    try:
        get_db_path()
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok",
        service="LegalMetrix Unified Inspection Backend",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        mock_ai=False,
        mock_compliance=False,
        database_status=db_status,
        uploads_dir=str(get_upload_base_dir()),
    )


# ------------------ Scan Endpoints (Real AI/OCR + Compliance Pipeline) ------------------ #
@router.post(
    "/inspection/scan",
    response_model=ComplianceEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan Product Packaging Image & Evaluate Compliance",
)
@router.post(
    "/scan",
    response_model=ComplianceEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload & Inspect Packaging Photo (Unified Scan)",
)
async def scan_product_image(
    image: UploadFile = File(..., description="Product packaging image (JPEG, PNG, WebP)"),
    category: Optional[str] = Form(None, description="Optional product category (food, beverage, personal_care, household)"),
    inspection_id: Optional[str] = Form(None, description="Optional custom inspection ID"),
):
    """
    End-to-end production OCR and Legal Metrology compliance pipeline:
    Image Upload -> Validation -> Quality Check -> AI OCR -> Field Extraction -> Category Resolution -> Deterministic Compliance Evaluation -> SQLite Persistence.
    """
    # 1. Validate image upload
    if not image or not image.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file uploaded.",
        )

    content = await image.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode image. Please ensure the file is a valid JPEG, PNG, or WebP image.",
        )

    # 2. Run Real AI OCR & Extraction Pipeline
    try:
        pipeline = get_ai_pipeline()
        ai_result = pipeline.inspect_image(img, source_name=image.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )

    # 3. Check for critical image quality failure
    quality_info = ai_result.get("quality", {})
    if quality_info.get("status") == "BAD":
        issues = quality_info.get("issues", ["Image quality is insufficient for OCR"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image quality check failed: {', '.join(issues)}",
        )

    # 4. Determine Category
    target_category = category
    if not target_category or not target_category.strip():
        ai_cat = ai_result.get("category", "unknown")
        if ai_cat and ai_cat != "unknown":
            target_category = ai_cat
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product category could not be determined automatically from the image. Please specify 'category' (food, beverage, personal_care, household) in request.",
            )

    # 5. Map actual extracted fields to compliance format
    ai_fields = ai_result.get("fields", {})
    extracted, confidences, evidences = map_ai_fields_to_compliance(ai_fields, source_name=image.filename)

    # 6. Evaluate Compliance using real deterministic engine
    try:
        result = evaluate_compliance(
            category=target_category,
            extracted_data=extracted,
            confidence_data=confidences,
            evidence_data=evidences,
        )

        insp_id = db.save_inspection(
            category=target_category,
            extracted_data=extracted,
            evaluation_result=result,
            confidence_data=confidences,
            evidence_data=evidences,
            inspection_id=inspection_id,
            product_name=extracted.get("product_name"),
            brand=extracted.get("brand"),
            variant=extracted.get("variant"),
            mrp=extracted.get("mrp"),
            net_quantity=extracted.get("net_quantity"),
            manufacturer=extracted.get("manufacturer"),
            compliance_status=result.get("overall_status"),
            violations=[f for f in result.get("findings", []) if f.get("result") == "FAIL"],
            checks=result.get("findings", []),
            evidence=evidences,
            source="image",
            sync_status="synced",
        )
        result["inspection_id"] = insp_id
        result["image_quality"] = quality_info
        result["raw_ocr_count"] = len(ai_result.get("raw_ocr", []))

        return result
    except CategoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance evaluation failed: {str(e)}",
        )


@router.post(
    "/scan/360",
    response_model=ComplianceEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload & Inspect 360 Rotational Video",
    description="Processes rotational packaging video across sampled keyframes, fuses multi-view OCR declarations, and evaluates Legal Metrology compliance.",
)
async def scan_package_video_360(
    video: UploadFile = File(..., description="Rotational 360 video file (MP4, MOV, AVI, WebM)"),
    category: Optional[str] = Form(None, description="Optional product category"),
    inspection_id: Optional[str] = Form(None, description="Optional custom inspection ID"),
):
    # 1. Save video upload safely
    saved_path = await save_upload_file(video, is_video=True)

    # 2. Extract keyframes using OpenCV
    cap = cv2.VideoCapture(saved_path)
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not open video file for multi-angle inspection.",
        )

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video file contains no readable frames.",
        )

    # Sample up to 8 evenly spaced frames
    num_samples = min(max(total_frames, 1), 8)
    sample_indices = [int(i * total_frames / num_samples) for i in range(num_samples)]
    frames_dict = {}

    current_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if current_idx in sample_indices:
            frame_name = f"frame_{current_idx:04d}"
            frames_dict[frame_name] = frame
        current_idx += 1
    cap.release()

    if not frames_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract frames from video file.",
        )

    # 3. Run OCR on each frame
    try:
        pipeline = get_ai_pipeline()
        frame_results = {}
        for f_name, f_img in frames_dict.items():
            f_res = pipeline.inspect_image(f_img, source_name=f_name)
            frame_results[f_name] = f_res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"360 Video OCR processing failed: {str(e)}",
        )

    # 4. Multi-View Fusion
    fusion = get_multi_image_fusion()
    fused_ai_result = fusion.fuse_results(frame_results)

    if not fused_ai_result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video quality is insufficient across all frames for OCR inspection.",
        )

    # 5. Resolve Category
    target_category = category
    if not target_category or not target_category.strip():
        fused_cat = fused_ai_result.get("category", "unknown")
        if fused_cat and fused_cat != "unknown":
            target_category = fused_cat
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product category could not be determined from video. Please specify 'category' in request.",
            )

    # 6. Map fused fields
    extracted, confidences, evidences = map_ai_fields_to_compliance(
        fused_ai_result.get("fields", {}), source_name=video.filename
    )

    # 7. Evaluate Compliance
    try:
        result = evaluate_compliance(
            category=target_category,
            extracted_data=extracted,
            confidence_data=confidences,
            evidence_data=evidences,
        )

        insp_id = db.save_inspection(
            category=target_category,
            extracted_data=extracted,
            evaluation_result=result,
            confidence_data=confidences,
            evidence_data=evidences,
            inspection_id=inspection_id,
            product_name=extracted.get("product_name"),
            brand=extracted.get("brand"),
            variant=extracted.get("variant"),
            mrp=extracted.get("mrp"),
            net_quantity=extracted.get("net_quantity"),
            manufacturer=extracted.get("manufacturer"),
            compliance_status=result.get("overall_status"),
            violations=[f for f in result.get("findings", []) if f.get("result") == "FAIL"],
            checks=result.get("findings", []),
            evidence=evidences,
            source="video_360",
            file_path=saved_path,
            sync_status="synced",
        )
        result["inspection_id"] = insp_id
        result["image_quality"] = fused_ai_result.get("quality", {})
        result["raw_ocr_count"] = sum(len(r.get("raw_ocr", [])) for r in frame_results.values())

        return result
    except CategoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance evaluation failed: {str(e)}",
        )


# ------------------ Rules Endpoints ------------------ #
@router.get(
    "/rules/{category}",
    response_model=CategoryRulesResponse,
    summary="Get Rule Definitions for Category",
)
def get_category_rules(
    category: str = FPath(..., description="Product category identifier (e.g. food, beverage, personal_care, household)"),
):
    try:
        rules_data = get_rules_for_category(category)
        return rules_data
    except CategoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidRuleDefinitionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ------------------ Compliance Evaluation Endpoints ------------------ #
@router.post(
    "/compliance/evaluate",
    response_model=ComplianceEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Legal Metrology Compliance",
)
@router.post(
    "/compliance",
    response_model=ComplianceEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Legal Metrology Compliance Check (Unified)",
)
def evaluate_product_compliance(payload: ComplianceEvaluationRequest):
    """
    Evaluates extracted declarations against deterministic Legal Metrology rules.
    Supports both dictionary-based extractions and list-based OCR pipeline outputs.
    Routes low-confidence extractions (<60%) to manual review without fabricating legal violations.
    """
    try:
        extracted = dict(payload.extracted_data or {})
        confidences = dict(payload.confidence or {})
        evidences = dict(payload.evidence or {})

        if payload.extractions:
            for item in payload.extractions:
                extracted[item.field] = item.value
                if item.confidence is not None:
                    norm_c = _normalize_confidence_score(item.confidence)
                    if norm_c is not None:
                        confidences[item.field] = norm_c
                if item.evidence is not None:
                    evidences[item.field] = item.evidence

        result = evaluate_compliance(
            category=payload.category,
            extracted_data=extracted,
            confidence_data=confidences,
            evidence_data=evidences,
        )

        insp_id = db.save_inspection(
            category=payload.category,
            extracted_data=extracted,
            evaluation_result=result,
            confidence_data=confidences,
            evidence_data=evidences,
            inspection_id=payload.inspection_id,
            product_name=extracted.get("product_name"),
            brand=extracted.get("brand"),
            variant=extracted.get("variant"),
            mrp=extracted.get("mrp"),
            net_quantity=extracted.get("net_quantity"),
            manufacturer=extracted.get("manufacturer"),
            compliance_status=result.get("overall_status"),
            violations=[f for f in result.get("findings", []) if f.get("result") == "FAIL"],
            checks=result.get("findings", []),
            evidence=evidences,
            source="direct_compliance",
            sync_status="synced",
        )
        result["inspection_id"] = insp_id

        return result
    except CategoryNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance evaluation failed: {str(e)}",
        )


# ------------------ Officer Manual Review Endpoint ------------------ #
@router.post(
    "/compliance/manual-review",
    response_model=ManualReviewResultResponse,
    summary="Submit Officer Manual Review Action",
)
def submit_manual_review(payload: ManualReviewSubmission):
    """
    Applies an officer review action (CONFIRM, CORRECT, MARK_UNREADABLE).
    Preserves original AI value, confidence, evidence metadata, and records the audit decision.
    """
    base_item = create_manual_review_item(
        field=payload.field,
        ai_value=payload.ai_value,
        confidence=payload.confidence if payload.confidence is not None else 0.0,
        reason="Manual review submitted by officer",
        evidence=payload.evidence,
    )

    try:
        resolved_item = apply_manual_review(
            review_item=base_item,
            action=payload.action,
            reviewer_id=payload.reviewer_id,
            corrected_value=payload.corrected_value,
            notes=payload.notes,
        )

        if payload.inspection_id:
            db.record_manual_review(payload.inspection_id, resolved_item)

        return {
            "status": "SUCCESS",
            "review_record": resolved_item,
            "message": f"Review action '{payload.action}' successfully applied by officer '{payload.reviewer_id}'.",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ------------------ Reconciliation & Comparison Endpoints ------------------ #
@router.post(
    "/reconciliation/compare",
    response_model=ReconciliationResponse,
    summary="Reconcile Physical Package vs Online Listing",
)
@router.post(
    "/comparison",
    response_model=ReconciliationResponse,
    summary="Physical Packaging vs Online Catalog Reference Comparison (Unified)",
)
def reconcile_physical_vs_online(payload: ReconciliationRequest):
    """
    Reconciles physical package declarations against controlled online demo data using the deterministic comparator.
    Does not assume mismatch is automatically illegal.
    """
    result = compare_product(
        physical_data=payload.physical_data,
        online_data=payload.online_data,
        fields_to_compare=payload.fields_to_compare,
    )
    return result


# ------------------ Inspection History & Persistence Endpoints ------------------ #
@router.get(
    "/inspection/{inspection_id}",
    response_model=InspectionResponse,
    summary="Get Single Inspection Record by ID",
)
def get_inspection_by_id(
    inspection_id: str = FPath(..., description="Unique inspection identifier"),
):
    record = db.get_inspection(inspection_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection record with ID '{inspection_id}' was not found.",
        )
    return InspectionResponse(**record)


@router.get(
    "/inspections",
    response_model=InspectionListResponse,
    summary="List Paginated Inspection Records",
)
def list_inspections(
    limit: int = Query(50, ge=1, le=200, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    compliance_status: Optional[str] = Query(None, description="Filter by status (COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW)"),
    sync_status: Optional[str] = Query(None, description="Filter by sync_status (synced, pending)"),
):
    items, total = db.get_inspections(limit=limit, offset=offset, compliance_status=compliance_status, sync_status=sync_status)
    validated_items = []
    for item in items:
        try:
            validated_items.append(InspectionResponse(**item))
        except Exception:
            pass
    return InspectionListResponse(total=total, items=validated_items)


@router.get(
    "/inspections/same-product",
    response_model=List[InspectionResponse],
    summary="Find Same-Product Inspection History",
)
def get_same_product_inspections(
    brand: Optional[str] = Query(None, description="Brand name filter"),
    product_name: Optional[str] = Query(None, description="Product commodity name filter"),
    category: Optional[str] = Query(None, description="Product category filter"),
    variant: Optional[str] = Query(None, description="Variant filter"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
):
    records = db.get_same_product(brand=brand, product_name=product_name, category=category, variant=variant, limit=limit)
    results = []
    for r in records:
        try:
            results.append(InspectionResponse(**r))
        except Exception:
            pass
    return results


@router.get(
    "/inspections/{inspection_id}/history",
    summary="Retrieve Same-Product Historical Inspections",
)
def get_product_inspection_history(
    inspection_id: str = FPath(..., description="Target inspection ID"),
):
    current_insp = db.get_inspection(inspection_id)
    if not current_insp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    all_inspections = db.list_all_inspections()
    past_inspections = [i for i in all_inspections if i["inspection_id"] != inspection_id]

    matched_history = find_previous_inspections(
        current_product=current_insp.get("extracted_data", {}),
        previous_inspections=past_inspections,
    )

    return {
        "inspection_id": inspection_id,
        "product_name": current_insp.get("extracted_data", {}).get("product_name"),
        "historical_inspections_count": len(matched_history),
        "history": matched_history,
    }


@router.post(
    "/inspections/{inspection_id}/historical-comparison",
    response_model=HistoricalComparisonResponse,
    summary="Compare Current Inspection against History",
)
def compare_inspection_to_history(
    inspection_id: str = FPath(..., description="Current inspection ID"),
    payload: Optional[HistoricalComparisonRequest] = None,
):
    current_insp = db.get_inspection(inspection_id)
    curr_data = payload.current_data if (payload and payload.current_data) else (current_insp.get("extracted_data") if current_insp else None)

    if curr_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No current inspection data found for ID '{inspection_id}' and none provided in request.",
        )

    prev_data = payload.previous_data if (payload and payload.previous_data) else None

    if prev_data is None:
        all_inspections = db.list_all_inspections()
        past = [i for i in all_inspections if i["inspection_id"] != inspection_id]
        matched = find_previous_inspections(curr_data, past)
        if matched:
            prev_data = matched[-1].get("extracted_data")

    if prev_data is None:
        return {
            "inspection_id": inspection_id,
            "status": "UNAVAILABLE",
            "message": "No previous historical inspection found for this product.",
            "changes_count": 0,
            "changes": [],
            "compared_fields": {},
        }

    track_fields = payload.fields_to_track if payload else None
    result = compare_historical(
        previous_data=prev_data,
        current_data=curr_data,
        fields_to_track=track_fields,
    )
    result["inspection_id"] = inspection_id
    return result


# ------------------ Offline Sync Endpoints (Member 5 Integration) ------------------ #
@router.post(
    "/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Offline Inspection Records (Primary)",
)
@router.post(
    "/inspections/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Offline Inspection Records (Client Alias)",
)
async def sync_offline_records(request: Union[SyncRequest, List[SyncItem], Dict[str, Any]]):
    """
    Accepts a batch of offline inspection records and syncs them idempotently to the SQLite database.
    Supports wrapped SyncRequest object, raw JSON array, and flexible field mappings.
    """
    if isinstance(request, SyncRequest):
        records = [r.model_dump() for r in request.records]
    elif isinstance(request, list):
        records = [r.model_dump() if hasattr(r, "model_dump") else dict(r) for r in request]
    elif isinstance(request, dict) and "records" in request:
        records = request["records"]
    else:
        records = [dict(request)]

    logger.info(f"Sync request received with {len(records)} record(s).")
    result_data = db.process_sync_batch(records)

    return SyncResponse(
        total_received=result_data["total_received"],
        synced_count=result_data["synced_count"],
        failed_count=result_data["failed_count"],
        results=[SyncResultItem(**r) for r in result_data["results"]],
    )


# ------------------ Predefined SIH Demonstration Scenarios ------------------ #
PREDEFINED_SCENARIOS = {
    "scenario_1": {
        "scenario_id": "scenario_1",
        "name": "Scenario 1: Fully Compliant Product",
        "category": "food",
        "description": "All 7 required declarations extracted with high OCR confidence (>=90%).",
        "expected_result": "COMPLIANT",
        "payload": {
            "category": "food",
            "inspection_id": "DEMO-SCENARIO-1",
            "extracted_data": {
                "product_name": "ABC Premium Biscuits",
                "net_quantity": "500g",
                "mrp": "₹50",
                "manufacturer": "ABC Foods Ltd, Mumbai",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@abcfoods.com, 1800-111-222",
            },
            "confidence": {
                "product_name": 98.0,
                "net_quantity": 95.0,
                "mrp": 96.0,
                "manufacturer": 92.0,
                "country_of_origin": 97.0,
                "date_of_manufacture": 91.0,
                "consumer_care": 90.0,
            },
            "evidence": {
                "product_name": "frame_01",
                "net_quantity": "frame_01",
                "mrp": "frame_02",
                "manufacturer": "frame_03",
                "country_of_origin": "frame_03",
                "date_of_manufacture": "frame_02",
                "consumer_care": "frame_04",
            },
        },
    },
    "scenario_2": {
        "scenario_id": "scenario_2",
        "name": "Scenario 2: Potential Non-Compliance (Deterministic Rule Failure)",
        "category": "food",
        "description": "Mandatory MRP and Country of Origin declarations are missing from physical packaging.",
        "expected_result": "NON_COMPLIANT",
        "payload": {
            "category": "food",
            "inspection_id": "DEMO-SCENARIO-2",
            "extracted_data": {
                "product_name": "ABC Premium Biscuits",
                "net_quantity": "500g",
                "manufacturer": "ABC Foods Ltd",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@abcfoods.com",
            },
            "confidence": {
                "product_name": 98.0,
                "net_quantity": 95.0,
                "manufacturer": 92.0,
                "date_of_manufacture": 91.0,
                "consumer_care": 90.0,
            },
            "evidence": {
                "product_name": "frame_01",
                "net_quantity": "frame_01",
                "manufacturer": "frame_03",
            },
        },
    },
    "scenario_3": {
        "scenario_id": "scenario_3",
        "name": "Scenario 3: Low OCR Confidence / Manual Review Required",
        "category": "food",
        "description": "Manufacturer declaration extracted with low confidence (43% < 60%), requiring officer verification.",
        "expected_result": "NEEDS_REVIEW",
        "payload": {
            "category": "food",
            "inspection_id": "DEMO-SCENARIO-3",
            "extracted_data": {
                "product_name": "ABC Biscuits",
                "net_quantity": "500g",
                "mrp": "₹50",
                "manufacturer": "ABC Foods Ltd",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@abcfoods.com",
            },
            "confidence": {
                "product_name": 98.0,
                "mrp": 96.0,
                "net_quantity": 94.0,
                "manufacturer": 43.0,
                "country_of_origin": 92.0,
                "date_of_manufacture": 95.0,
                "consumer_care": 90.0,
            },
            "evidence": {
                "product_name": "frame_01",
                "mrp": "frame_02",
                "manufacturer": {"frame_id": "frame_03", "region": {"x": 120, "y": 240, "width": 300, "height": 80}},
            },
        },
    },
    "scenario_4": {
        "scenario_id": "scenario_4",
        "name": "Scenario 4: Physical vs Online Price Mismatch Reconciliation",
        "category": "reconciliation",
        "description": "Physical MRP ₹50 vs Online Catalog MRP ₹60 for identical 500g net quantity.",
        "expected_result": "MISMATCH",
        "payload": {
            "physical_data": {
                "product_name": "Demo Biscuits",
                "mrp": "₹50",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India",
            },
            "online_data": {
                "product_name": "Demo Biscuits",
                "mrp": "₹60",
                "net_quantity": "500 g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India",
            },
        },
    },
    "scenario_5": {
        "scenario_id": "scenario_5",
        "name": "Scenario 5: Same-Product Historical MRP Increase Detection",
        "category": "historical",
        "description": "Previous inspection recorded MRP ₹50; current inspection recorded MRP ₹60.",
        "expected_result": "CHANGE_DETECTED",
        "payload": {
            "previous_data": {
                "brand": "DemoBrand",
                "product_name": "Demo Product",
                "category": "food",
                "variant": "500g",
                "mrp": "₹50",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
            },
            "current_data": {
                "brand": "DemoBrand",
                "product_name": "Demo Product",
                "category": "food",
                "variant": "500g",
                "mrp": "₹60",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
            },
        },
    },
}


@router.get(
    "/demo/scenarios",
    response_model=List[DemoScenarioItem],
    summary="List Predefined SIH Demonstration Scenarios",
)
def list_demo_scenarios():
    return [
        DemoScenarioItem(
            scenario_id=v["scenario_id"],
            name=v["name"],
            category=v["category"],
            description=v["description"],
            expected_result=v["expected_result"],
        )
        for v in PREDEFINED_SCENARIOS.values()
    ]


@router.post(
    "/demo/run-scenario/{scenario_id}",
    summary="Run Predefined SIH Demonstration Scenario",
)
def run_demo_scenario(
    scenario_id: str = FPath(..., description="scenario_1, scenario_2, scenario_3, scenario_4, scenario_5"),
):
    scenario = PREDEFINED_SCENARIOS.get(scenario_id.lower())
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found. Permitted: {list(PREDEFINED_SCENARIOS.keys())}",
        )

    if scenario["category"] == "food":
        payload = ComplianceEvaluationRequest(**scenario["payload"])
        res = evaluate_product_compliance(payload)
        return {
            "scenario": scenario["name"],
            "expected_result": scenario["expected_result"],
            "result": res,
        }
    elif scenario["category"] == "reconciliation":
        payload = ReconciliationRequest(**scenario["payload"])
        res = reconcile_physical_vs_online(payload)
        return {
            "scenario": scenario["name"],
            "expected_result": scenario["expected_result"],
            "result": res,
        }
    elif scenario["category"] == "historical":
        payload = HistoricalComparisonRequest(**scenario["payload"])
        res = compare_historical(
            previous_data=payload.previous_data,
            current_data=payload.current_data,
        )
        return {
            "scenario": scenario["name"],
            "expected_result": scenario["expected_result"],
            "result": res,
        }
