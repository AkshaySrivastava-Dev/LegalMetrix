"""
AI & OCR Module for LegalMetrix.

Provides OCR extraction, field extraction, quality checks, category classification,
confidence calculation, multi-image fusion, deterministic brand fallback rules,
configurable product safety alerts, prototype health scores, fraud anomaly detection,
and evidence generation.
"""

from ai.ocr_engine import OCREngine, create_ocr_engine
from ai.nvidia_ocr import NVIDIAOCREngine, create_nvidia_ocr_engine
from ai.preprocess import (
    enhance_contrast,
    sharpen_image,
    enhance_dot_matrix,
    detect_barcode,
    preprocess_for_ocr,
)
from ai.field_extractor import FieldExtractor
from ai.business_rules import apply_business_rules, BRAND_RULES
from ai.safety_rules import evaluate_product_safety, SAFETY_RULES_REGISTRY
from ai.health_score import evaluate_health_score, HEALTH_SCORES_REGISTRY
from ai.fraud_detection import evaluate_fraud_and_review, PRODUCT_REFERENCE_RULES
from ai.image_quality import check_image_quality
from ai.category import classify_category
from ai.confidence import add_confidence_levels
from ai.evidence import save_evidence_image
from ai.multi_image import MultiImageFusion, create_fusion
from ai.pipeline import InspectionAI, create_pipeline

__all__ = [
    "OCREngine",
    "create_ocr_engine",
    "NVIDIAOCREngine",
    "create_nvidia_ocr_engine",
    "enhance_contrast",
    "sharpen_image",
    "enhance_dot_matrix",
    "detect_barcode",
    "preprocess_for_ocr",
    "FieldExtractor",
    "apply_business_rules",
    "BRAND_RULES",
    "evaluate_product_safety",
    "SAFETY_RULES_REGISTRY",
    "evaluate_health_score",
    "HEALTH_SCORES_REGISTRY",
    "evaluate_fraud_and_review",
    "PRODUCT_REFERENCE_RULES",
    "check_image_quality",
    "classify_category",
    "add_confidence_levels",
    "save_evidence_image",
    "MultiImageFusion",
    "create_fusion",
    "InspectionAI",
    "create_pipeline",
]
