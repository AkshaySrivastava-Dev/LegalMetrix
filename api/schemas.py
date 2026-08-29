"""
Pydantic Schemas for LegalMetrix API Endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------ Rule Schemas ------------------ #
class RuleDefinitionItem(BaseModel):
    rule_id: str
    category: str
    field: str
    required: bool
    description: str
    source: str
    version: str
    validation: Optional[Dict[str, Any]] = None


class CategoryRulesResponse(BaseModel):
    category: str
    version: str
    description: Optional[str] = None
    rules: List[RuleDefinitionItem]


# ------------------ Compliance Schemas ------------------ #
class ExtractionItem(BaseModel):
    field: str = Field(..., description="Field name (e.g. mrp, net_quantity, manufacturer)")
    value: Optional[Any] = Field(None, description="Extracted text/value")
    confidence: Optional[float] = Field(None, description="Confidence score (0-100 or 0.0-1.0)")
    evidence: Optional[Any] = Field(None, description="Frame ID or bounding box coordinates")


class ComplianceEvaluationRequest(BaseModel):
    category: str = Field(..., description="Product category, e.g. food, beverage, personal_care, household")
    inspection_id: Optional[str] = Field(None, description="Optional unique inspection identifier")
    extracted_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Key-value dictionary of extracted fields")
    confidence: Optional[Dict[str, float]] = Field(default_factory=dict, description="Per-field confidence scores")
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Per-field evidence (frame_id, region, etc.)")
    extractions: Optional[List[ExtractionItem]] = Field(None, description="Alternative list format for structured OCR pipeline outputs")


class FindingModel(BaseModel):
    rule_id: str
    rule_version: str
    field: str
    required: bool
    requirement: str
    result: str = Field(..., description="PASS, FAIL, or UNCERTAIN")
    reason: str
    extracted_value: Optional[Any] = None
    confidence: float
    confidence_tier: str
    evidence: Optional[Any] = None
    source: str


class ManualReviewItemModel(BaseModel):
    field: str
    rule_id: Optional[str] = None
    ai_value: Optional[Any] = None
    confidence: float
    reason: str
    evidence: Optional[Any] = None
    status: str
    requires_manual_review: bool
    created_at: str
    resolved_at: Optional[str] = None
    action: Optional[str] = None
    corrected_value: Optional[Any] = None
    reviewer_id: Optional[str] = None
    notes: Optional[str] = None


class ComplianceEvaluationResponse(BaseModel):
    inspection_id: Optional[str] = None
    category: str
    definition_version: str
    overall_status: str = Field(..., description="COMPLIANT, NON_COMPLIANT, or NEEDS_REVIEW")
    summary: str
    evaluated_at: str
    total_rules_evaluated: int
    passed_count: int
    failed_count: int
    uncertain_count: int
    findings: List[FindingModel]
    manual_reviews: List[ManualReviewItemModel]
    image_quality: Optional[Dict[str, Any]] = Field(None, description="Optional image quality diagnostic metrics")
    raw_ocr_count: Optional[int] = Field(None, description="Count of raw OCR text lines detected")


# ------------------ Manual Review Schemas ------------------ #
class ManualReviewSubmission(BaseModel):
    inspection_id: Optional[str] = Field(None, description="Inspection ID if tracking session")
    field: str = Field(..., description="Field name being reviewed")
    action: str = Field(..., description="CONFIRM, CORRECT, or MARK_UNREADABLE")
    reviewer_id: str = Field(..., description="Legal Metrology Officer ID")
    ai_value: Optional[Any] = Field(None, description="Original AI value if submitting standalone")
    confidence: Optional[float] = Field(None, description="Original AI confidence")
    evidence: Optional[Any] = Field(None, description="Original evidence reference")
    corrected_value: Optional[Any] = Field(None, description="Corrected value required if action is CORRECT")
    notes: Optional[str] = Field(None, description="Officer notes / remarks")


class ManualReviewResultResponse(BaseModel):
    status: str
    review_record: Dict[str, Any]
    message: str


# ------------------ Reconciliation Schemas ------------------ #
class ReconciliationRequest(BaseModel):
    physical_data: Dict[str, Any] = Field(..., description="Declarations extracted from physical package")
    online_data: Dict[str, Any] = Field(..., description="Declarations from online catalog demo")
    fields_to_compare: Optional[List[str]] = Field(None, description="Specific fields to compare")


class FieldComparisonModel(BaseModel):
    physical: Optional[Any] = None
    online: Optional[Any] = None
    result: str = Field(..., description="MATCH, MISMATCH, or UNAVAILABLE")
    reason: Optional[str] = None


class ReconciliationResponse(BaseModel):
    overall: str = Field(..., description="MATCH, MISMATCH, or UNAVAILABLE")
    message: str
    matches_count: int
    mismatches_count: int
    unavailable_count: int
    fields: Dict[str, FieldComparisonModel]


# ------------------ Historical Schemas ------------------ #
class HistoricalChangeModel(BaseModel):
    field: str
    previous: Optional[Any] = None
    current: Optional[Any] = None
    status: str = Field(default="CHANGE_DETECTED")
    reason: Optional[str] = None


class HistoricalComparisonRequest(BaseModel):
    current_data: Optional[Dict[str, Any]] = None
    previous_data: Optional[Dict[str, Any]] = None
    fields_to_track: Optional[List[str]] = None


class HistoricalComparisonResponse(BaseModel):
    inspection_id: Optional[str] = None
    status: str = Field(..., description="CHANGE_DETECTED, NO_CHANGE, or UNAVAILABLE")
    message: str
    changes_count: int
    changes: List[HistoricalChangeModel]
    compared_fields: Dict[str, Any]


# ------------------ Demo Scenario Schemas ------------------ #
class DemoScenarioItem(BaseModel):
    scenario_id: str
    name: str
    category: str
    description: str
    expected_result: str


# ------------------ Member 2 Backend Schemas ------------------ #
class ComplianceCheck(BaseModel):
    field: str
    rule: str
    passed: bool
    detected_value: Optional[str] = None
    message: Optional[str] = None


class ComplianceViolation(BaseModel):
    field: str
    rule: str
    severity: str = "medium"
    issue: str
    suggestion: Optional[str] = None


class ComplianceResult(BaseModel):
    compliance_status: str = "NON_COMPLIANT"
    confidence: float = 0.0
    checks: List[ComplianceCheck] = Field(default_factory=list)
    violations: List[ComplianceViolation] = Field(default_factory=list)
    summary: Optional[str] = None


class AIAnalysisResult(BaseModel):
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    variant: Optional[str] = None
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence: float = 0.0
    raw_text: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: Optional[str] = "image"


class InspectionBase(BaseModel):
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    variant: Optional[str] = None
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence: float = 0.0
    compliance_status: str = "UNKNOWN"
    violations: List[Any] = Field(default_factory=list)
    checks: List[Any] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict)
    source: Optional[str] = "image"
    sync_status: str = "synced"


class InspectionCreate(InspectionBase):
    inspection_id: Optional[str] = None
    created_at: Optional[str] = None


class InspectionResponse(InspectionBase):
    inspection_id: str
    created_at: str
    file_path: Optional[str] = None


class InspectionListResponse(BaseModel):
    total: int
    items: List[InspectionResponse]


class SyncItem(BaseModel):
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
    source: Optional[str] = "offline_sync"
    created_at: Optional[str] = None
    sync_status: Optional[str] = "pending"
    device_id: Optional[str] = None
    client_timestamp: Optional[str] = None


class SyncRequest(BaseModel):
    records: List[SyncItem]


class SyncResultItem(BaseModel):
    inspection_id: str
    status: str
    action: str
    reason: Optional[str] = None


class SyncResponse(BaseModel):
    total_received: int
    synced_count: int
    failed_count: int
    results: List[SyncResultItem]


class ComparisonRequest(BaseModel):
    inspection_id: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    variant: Optional[str] = None
    mrp: Optional[str] = None
    net_quantity: Optional[str] = None
    manufacturer: Optional[str] = None


class FieldComparison(BaseModel):
    field: str
    physical_value: Optional[str] = None
    online_value: Optional[str] = None
    matched: bool
    note: Optional[str] = None


class ComparisonResponse(BaseModel):
    status: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    matched_fields: List[str] = Field(default_factory=list)
    mismatched_fields: List[str] = Field(default_factory=list)
    details: List[FieldComparison] = Field(default_factory=list)
    online_source: Optional[str] = "Controlled Demo Catalog"
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"
    timestamp: str
    mock_ai: bool
    mock_compliance: bool
    database_status: str
    uploads_dir: str

