"""
Main Inspection Pipeline for LegalMetrix AI.

Orchestrates the complete flow:
IMAGE -> QUALITY CHECK -> PREPROCESSING -> OCR -> FIELD EXTRACTION -> CATEGORY -> CONFIDENCE -> MULTI-IMAGE FUSION -> BUSINESS RULES -> EVIDENCE -> JSON RESULT
"""

import os
import json
from typing import Dict, Any, Optional, List
import cv2
import numpy as np

from ai.ocr_engine import OCREngine, create_ocr_engine
from ai.preprocess import preprocess_for_ocr, detect_barcode
from ai.image_quality import check_image_quality
from ai.field_extractor import FieldExtractor
from ai.category import classify_category
from ai.confidence import add_confidence_levels
from ai.evidence import save_evidence_image
from ai.multi_image import MultiImageFusion, create_fusion
from ai.business_rules import apply_business_rules


class InspectionAI:
    """Main pipeline for packaged commodity inspection."""

    def __init__(
        self,
        ocr_engine: Optional[Any] = None,
        field_extractor: Optional[FieldExtractor] = None,
        save_evidence: bool = True,
        evidence_dir: str = "evidence"
    ):
        """
        Initialize inspection pipeline.

        Args:
            ocr_engine: OCR engine instance (creates default if None)
            field_extractor: Field extractor instance (creates default if None)
            save_evidence: Whether to save evidence images
            evidence_dir: Directory for evidence images
        """
        self.ocr_engine = ocr_engine or create_ocr_engine()
        self.field_extractor = field_extractor or FieldExtractor()
        self.save_evidence = save_evidence
        self.evidence_dir = evidence_dir

        if save_evidence:
            os.makedirs(evidence_dir, exist_ok=True)

    def inspect_image(
        self,
        image: np.ndarray,
        source_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete inspection on an image.

        Args:
            image: OpenCV image (numpy array, BGR format)
            source_name: Optional source identifier (e.g., filename)

        Returns:
            JSON-serializable inspection result
        """
        # Step 1: Image Quality Check
        quality = check_image_quality(image)

        # Step 2: Barcode Detection
        barcode_info = detect_barcode(image)

        # If quality is BAD, return early with quality info
        if quality.get("status") == "BAD":
            return {
                "success": False,
                "quality": quality,
                "category": "unknown",
                "barcode": barcode_info,
                "fields": {},
                "raw_ocr": [],
                "message": "Image quality insufficient for reliable OCR"
            }

        # Step 3: Image Preprocessing & OCR
        preprocessed = preprocess_for_ocr(image)
        ocr_results = self.ocr_engine.run_ocr(preprocessed)
        if not ocr_results:
            # Fallback to raw image if preprocessed yielded no results
            ocr_results = self.ocr_engine.run_ocr(image)

        if not ocr_results:
            return {
                "success": True,
                "quality": quality,
                "category": "unknown",
                "barcode": barcode_info,
                "fields": {},
                "raw_ocr": [],
                "message": "No text detected in image"
            }

        # Step 4: Extract category from OCR texts
        ocr_texts = [item['text'] for item in ocr_results]
        category_result = classify_category(ocr_texts)
        category = category_result.get("category", "unknown")

        # Step 5: Extract fields
        fields = self.field_extractor.extract_all(ocr_results, source=source_name)

        # Step 6: Add confidence levels
        fields = add_confidence_levels(fields)

        # Step 7: Apply deterministic brand & business rules
        fields = apply_business_rules(fields)

        # Step 8: Save evidence images
        evidence_paths = {}
        if self.save_evidence and source_name:
            base_name = os.path.splitext(os.path.basename(source_name))[0]
            evidence_paths = save_evidence_image(
                image, base_name, ocr_results, fields, self.evidence_dir
            )

        # Step 9: Build result
        result = {
            "success": True,
            "quality": quality,
            "category": category,
            "barcode": barcode_info,
            "fields": fields,
            "raw_ocr": ocr_results,
            "evidence": evidence_paths
        }

        return result

    def inspect_image_file(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """Inspect an image file."""
        image = cv2.imread(image_path)
        if image is None:
            return {
                "success": False,
                "error": f"Failed to load image: {image_path}"
            }
        return self.inspect_image(image, source_name=image_path)

    def to_json(self, result: Dict[str, Any]) -> str:
        """Convert result to JSON string."""
        return json.dumps(result, indent=2, default=str)

    def inspect_product(
        self,
        front_image: np.ndarray,
        back_image: np.ndarray,
        side_image: np.ndarray,
        top_image: Optional[np.ndarray] = None,
        front_name: str = "front.jpg",
        back_name: str = "back.jpg",
        side_name: str = "side.jpg",
        top_name: str = "top.jpg"
    ) -> Dict[str, Any]:
        """
        Run complete inspection on multiple product views.

        Args:
            front_image: Front view OpenCV image
            back_image: Back view OpenCV image
            side_image: Side view OpenCV image
            top_image: Optional top view OpenCV image
            front_name: Source name for front image
            back_name: Source name for back image
            side_name: Source name for side image
            top_name: Source name for top image

        Returns:
            JSON-serializable fused inspection result
        """
        images = {
            'front': (front_image, front_name),
            'back': (back_image, back_name),
            'side': (side_image, side_name)
        }
        if top_image is not None and getattr(top_image, 'size', 0) > 0:
            images['top'] = (top_image, top_name)

        single_results = {}
        for source_name, (image, name) in images.items():
            if image is None or getattr(image, 'size', 0) == 0:
                single_results[source_name] = {
                    'success': False,
                    'error': f'Empty image for {source_name}'
                }
                continue
            single_results[source_name] = self.inspect_image(image, source_name=name)

        # Fuse results across all views
        fusion = create_fusion()
        fused_result = fusion.fuse_results(single_results)

        # Add confidence levels to fused fields
        fused_result['fields'] = add_confidence_levels(fused_result.get('fields', {}))

        # Apply deterministic brand rules post-fusion
        fused_result['fields'] = apply_business_rules(fused_result.get('fields', {}))

        # Add image filenames
        fused_result['images'] = {
            'front': front_name,
            'back': back_name,
            'side': side_name
        }
        if 'top' in images:
            fused_result['images']['top'] = top_name

        return fused_result

    def inspect_product_files(
        self,
        front_path: str,
        back_path: str,
        side_path: str,
        top_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Inspect product from image files."""
        front_image = cv2.imread(front_path)
        back_image = cv2.imread(back_path)
        side_image = cv2.imread(side_path)
        top_image = cv2.imread(top_path) if top_path and os.path.exists(top_path) else None

        if front_image is None:
            return {'success': False, 'error': f'Failed to load front image: {front_path}'}
        if back_image is None:
            return {'success': False, 'error': f'Failed to load back image: {back_path}'}
        if side_image is None:
            return {'success': False, 'error': f'Failed to load side image: {side_path}'}

        return self.inspect_product(
            front_image, back_image, side_image, top_image,
            front_name=os.path.basename(front_path),
            back_name=os.path.basename(back_path),
            side_name=os.path.basename(side_path),
            top_name=os.path.basename(top_path) if top_path else "top.jpg"
        )


def create_pipeline(
    use_gpu: bool = False,
    save_evidence: bool = True,
    evidence_dir: str = "evidence",
    text_det_thresh: float = 0.3,
    text_det_box_thresh: float = 0.5,
    backend: str = "auto",
    api_key: Optional[str] = None
) -> InspectionAI:
    """Factory function to create inspection pipeline."""
    ocr_engine = create_ocr_engine(
        use_gpu=use_gpu,
        backend=backend,
        text_det_thresh=text_det_thresh,
        text_det_box_thresh=text_det_box_thresh,
        api_key=api_key
    )
    field_extractor = FieldExtractor()
    return InspectionAI(
        ocr_engine=ocr_engine,
        field_extractor=field_extractor,
        save_evidence=save_evidence,
        evidence_dir=evidence_dir
    )
