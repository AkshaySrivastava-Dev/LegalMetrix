"""
AI & OCR Module for LegalMetrix (Member 3 AI Pipeline).

Provides OCR extraction, field extraction, quality checks, category classification,
confidence calculation, multi-image fusion, and evidence generation.
"""

from ai.ocr_engine import OCREngine, create_ocr_engine
from ai.field_extractor import FieldExtractor
from ai.image_quality import check_image_quality
from ai.category import classify_category
from ai.confidence import add_confidence_levels
from ai.evidence import save_evidence_image
from ai.multi_image import MultiImageFusion, create_fusion
from ai.pipeline import InspectionAI

__all__ = [
    "OCREngine",
    "create_ocr_engine",
    "FieldExtractor",
    "check_image_quality",
    "classify_category",
    "add_confidence_levels",
    "save_evidence_image",
    "MultiImageFusion",
    "create_fusion",
    "InspectionAI",
]
