"""
FastAPI Route Handlers for Member 4: LegalMetrix Compliance & Comparison API.
"""

from typing import Any, Dict, List, Optional, Tuple
import cv2
from fastapi import APIRouter, File, Form, HTTPException, Path as FPath, UploadFile, status
import numpy as np

from api.schemas import (
    CategoryRulesResponse,
    ComplianceEvaluationRequest,
    ComplianceEvaluationResponse,
    DemoScenarioItem,
    HistoricalComparisonRequest,
    HistoricalComparisonResponse,
    ManualReviewResultResponse,
    ManualReviewSubmission,
    ReconciliationRequest,
    ReconciliationResponse,
)
from api.storage import db
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

router = APIRouter(prefix="/api", tags=["LegalMetrix"])

_ai_pipeline = None


def get_ai_pipeline():
    """
    Lazy loader for InspectionAI pipeline to avoid loading heavy OCR models at import time.
    """
    global _ai_pipeline
    if _ai_pipeline is None:
        from ai.pipeline import InspectionAI
        _ai_pipeline = InspectionAI(save_evidence=False)
    return _ai_pipeline


def map_ai_fields_to_compliance(
    ai_fields: Dict[str, Any],
    source_name: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, Any]]:
    """
    Maps fields output from ai.field_extractor to LegalMetrix compliance evaluation format.
    """
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

    # Also copy any extra direct fields from ai_fields that weren't in field_keys
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
    """
    Normalizes confidence scores whether provided as percentages (0-100) or decimal probabilities (0.0-1.0).
    """
    if val is None:
        return None
    try:
        f = float(val)
        # If float is between 0 and 1.0 (excluding exactly 0.0), scale to percentage
        if 0.0 < f <= 1.0:
            return round(f * 100.0, 2)
        return round(f, 2)
    except (ValueError, TypeError):
        return None


# ------------------ Rules Endpoints ------------------ #
@router.get(
    "/rules/{category}",
    response_model=CategoryRulesResponse,
    summary="Get Rule Definitions for Category",
)
def get_category_rules(
    category: str = FPath(..., description="Product category identifier (e.g. food, beverage, personal_care, household)"),
):
    """
    Retrieves the active deterministic rule definitions for the specified product category.
    """
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


# ------------------ Compliance Endpoints ------------------ #
@router.post(
    "/compliance/evaluate",
    response_model=ComplianceEvaluationResponse,
    summary="Evaluate Legal Metrology Compliance",
)
def evaluate_product_compliance(payload: ComplianceEvaluationRequest):
    """
    Evaluates AI/OCR extracted declarations against deterministic Legal Metrology rules.
    Supports both dictionary-based extractions and list-based OCR pipeline outputs.
    Routes low-confidence extractions (<60%) to manual review without fabricating legal violations.
    """
    try:
        extracted = dict(payload.extracted_data or {})
        confidences = dict(payload.confidence or {})
        evidences = dict(payload.evidence or {})

        # If alternative extractions list format is supplied, merge seamlessly
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


@router.post(
    "/inspection/scan",
    response_model=ComplianceEvaluationResponse,
    summary="Scan Product Packaging Image & Evaluate Compliance",
)
async def scan_product_image(
    image: UploadFile = File(..., description="Product packaging image (JPEG, PNG, WebP)"),
    category: Optional[str] = Form(None, description="Optional product category (food, beverage, personal_care, household). Auto-detected if omitted."),
    inspection_id: Optional[str] = Form(None, description="Optional custom inspection ID"),
):
    """
    End-to-end OCR and Legal Metrology compliance pipeline:
    Image Upload -> Quality Check -> PaddleOCR -> Field Extraction -> Category Resolution -> Deterministic Compliance Evaluation.
    """
    # 1. Validate image upload
    if not image or not image.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file uploaded.",
        )

    # Read image bytes
    content = await image.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    # Decode image with OpenCV
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode image. Please ensure the file is a valid JPEG, PNG, or WebP image.",
        )

    # 2. Run AI OCR & Extraction Pipeline
    try:
        pipeline = get_ai_pipeline()
        ai_result = pipeline.inspect_image(img, source_name=image.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )

    # Check for critical image quality failure
    quality_info = ai_result.get("quality", {})
    if quality_info.get("status") == "BAD":
        issues = quality_info.get("issues", ["Image quality is insufficient for OCR"])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image quality check failed: {', '.join(issues)}",
        )

    # 3. Determine Category
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

    # 4. Map extracted fields to compliance format
    ai_fields = ai_result.get("fields", {})
    extracted, confidences, evidences = map_ai_fields_to_compliance(ai_fields, source_name=image.filename)

    # 5. Evaluate Compliance using existing deterministic engine
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


# ------------------ Reconciliation Endpoints ------------------ #
@router.post(
    "/reconciliation/compare",
    response_model=ReconciliationResponse,
    summary="Reconcile Physical Package vs Online Listing",
)
def reconcile_physical_vs_online(payload: ReconciliationRequest):
    """
    Reconciles physical package declarations against controlled online demo data.
    Does not assume mismatch is automatically illegal.
    """
    result = compare_product(
        physical_data=payload.physical_data,
        online_data=payload.online_data,
        fields_to_compare=payload.fields_to_compare,
    )
    return result


# ------------------ Historical Comparison Endpoints ------------------ #
@router.get(
    "/inspections/{inspection_id}/history",
    summary="Retrieve Same-Product Historical Inspections",
)
def get_product_inspection_history(
    inspection_id: str = FPath(..., description="Target inspection ID"),
):
    """
    Finds past inspections matching the same product identity (brand, product_name, category, variant).
    """
    current_insp = db.get_inspection(inspection_id)
    if not current_insp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    all_inspections = db.list_all_inspections()
    past_inspections = [i for i in all_inspections if i["inspection_id"] != inspection_id]

    matched_history = find_previous_inspections(
        current_product=current_insp["extracted_data"],
        previous_inspections=past_inspections,
    )

    return {
        "inspection_id": inspection_id,
        "product_name": current_insp["extracted_data"].get("product_name"),
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
    """
    Compares the current inspection declarations with a previous inspection.
    Detects changes (e.g. MRP increase, quantity changes) over time.
    """
    current_insp = db.get_inspection(inspection_id)
    curr_data = payload.current_data if (payload and payload.current_data) else (current_insp["extracted_data"] if current_insp else None)

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


# ------------------ Demo & Hackathon Scenario Endpoints ------------------ #
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
    """
    Returns list of 5 predefined demonstration scenarios for quick testing and UI simulation.
    """
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
    """
    Directly executes one of the 5 controlled SIH demonstration scenarios and returns the full result.
    """
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
