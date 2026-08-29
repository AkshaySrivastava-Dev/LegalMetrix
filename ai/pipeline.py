"""
Main Inspection Pipeline.

Orchestrates the complete flow:
IMAGE -> QUALITY CHECK -> OCR -> FIELD EXTRACTION -> CATEGORY -> CONFIDENCE -> EVIDENCE -> JSON RESULT

Supports both single-image and multi-image (3-view) inspection.
"""

import os
import json
from typing import Dict, Any, Optional, List
import cv2
import numpy as np

try:
    from ai.ocr_engine import OCREngine, create_ocr_engine
    from ai.image_quality import check_image_quality
    from ai.field_extractor import FieldExtractor
    from ai.category import classify_category
    from ai.confidence import add_confidence_levels
    from ai.evidence import save_evidence_image
    from ai.multi_image import MultiImageFusion, create_fusion
except ImportError:
    from ocr_engine import OCREngine, create_ocr_engine
    from image_quality import check_image_quality
    from field_extractor import FieldExtractor
    from category import classify_category
    from confidence import add_confidence_levels
    from evidence import save_evidence_image
    from multi_image import MultiImageFusion, create_fusion


class InspectionAI:
    """Main pipeline for packaged commodity inspection."""
    
    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
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
        
        # If quality is BAD, return early with quality info
        if quality["status"] == "BAD":
            return {
                "success": False,
                "quality": quality,
                "category": "unknown",
                "fields": {},
                "raw_ocr": [],
                "message": "Image quality insufficient for reliable OCR"
            }
        
        # Step 2: Run OCR
        ocr_results = self.ocr_engine.run_ocr(image)
        
        if not ocr_results:
            return {
                "success": True,
                "quality": quality,
                "category": "unknown",
                "fields": {},
                "raw_ocr": [],
                "message": "No text detected in image"
            }
        
        # Step 3: Extract category from OCR texts
        ocr_texts = [item['text'] for item in ocr_results]
        category_result = classify_category(ocr_texts)
        category = category_result["category"]
        
        # Step 4: Extract fields
        fields = self.field_extractor.extract_all(ocr_results, source=source_name)
        
        # Step 5: Add confidence levels
        fields = add_confidence_levels(fields)
        
        # Step 6: Save evidence images
        evidence_paths = {}
        if self.save_evidence and source_name:
            base_name = os.path.splitext(os.path.basename(source_name))[0]
            evidence_paths = save_evidence_image(
                image, base_name, ocr_results, fields, self.evidence_dir
            )
        
        # Step 7: Build result
        result = {
            "success": True,
            "quality": quality,
            "category": category,
            "fields": fields,
            "raw_ocr": ocr_results,
            "evidence": evidence_paths
        }
        
        return result
    
    def inspect_image_file(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Inspect an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            JSON-serializable inspection result
        """
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
        front_name: str = "front.jpg",
        back_name: str = "back.jpg",
        side_name: str = "side.jpg"
    ) -> Dict[str, Any]:
        """
        Run complete inspection on three product views.
        
        Args:
            front_image: Front view OpenCV image
            back_image: Back view OpenCV image
            side_image: Side view OpenCV image
            front_name: Source name for front image
            back_name: Source name for back image
            side_name: Source name for side image
            
        Returns:
            JSON-serializable fused inspection result
        """
        # Process each image independently
        images = {
            'front': (front_image, front_name),
            'back': (back_image, back_name),
            'side': (side_image, side_name)
        }
        
        single_results = {}
        for source_name, (image, name) in images.items():
            if image is None or image.size == 0:
                single_results[source_name] = {
                    'success': False,
                    'error': f'Empty image for {source_name}'
                }
                continue
            single_results[source_name] = self.inspect_image(image, source_name=name)
        
        # Fuse results
        fusion = create_fusion()
        fused_result = fusion.fuse_results(single_results)
        
        # Add confidence levels to fused fields
        fused_result['fields'] = add_confidence_levels(fused_result['fields'])
        
        # Add image filenames to result
        fused_result['images'] = {
            'front': front_name,
            'back': back_name,
            'side': side_name
        }
        
        return fused_result
    
    def inspect_product_files(
        self,
        front_path: str,
        back_path: str,
        side_path: str
    ) -> Dict[str, Any]:
        """
        Inspect product from three image files.
        
        Args:
            front_path: Path to front view image
            back_path: Path to back view image
            side_path: Path to side view image
            
        Returns:
            JSON-serializable fused inspection result
        """
        front_image = cv2.imread(front_path)
        back_image = cv2.imread(back_path)
        side_image = cv2.imread(side_path)
        
        if front_image is None:
            return {'success': False, 'error': f'Failed to load front image: {front_path}'}
        if back_image is None:
            return {'success': False, 'error': f'Failed to load back image: {back_path}'}
        if side_image is None:
            return {'success': False, 'error': f'Failed to load side image: {side_path}'}
        
        return self.inspect_product(
            front_image, back_image, side_image,
            front_name=os.path.basename(front_path),
            back_name=os.path.basename(back_path),
            side_name=os.path.basename(side_path)
        )


def create_pipeline(
    use_gpu: bool = False,
    save_evidence: bool = True,
    evidence_dir: str = "evidence",
    text_det_thresh: float = 0.3,
    text_det_box_thresh: float = 0.5
) -> InspectionAI:
    """Factory function to create inspection pipeline."""
    ocr_engine = create_ocr_engine(
        use_gpu=use_gpu,
        text_det_thresh=text_det_thresh,
        text_det_box_thresh=text_det_box_thresh
    )
    field_extractor = FieldExtractor()
    return InspectionAI(
        ocr_engine=ocr_engine,
        field_extractor=field_extractor,
        save_evidence=save_evidence,
        evidence_dir=evidence_dir
    )


if __name__ == "__main__":
    # Test with synthetic image
    import numpy as np
    
    # Larger image with gray background (not pure white)
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)  # Gray background
    cv2.putText(img, 'MRP Rs. 50', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, 'Net Qty: 200 g', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, 'Manufactured by ABC Foods Ltd', (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, 'Mfd 27/11/25', (50, 350), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, 'Exp 27/11/26', (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, 'Batch No: B12345', (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, 'ABC', (50, 500), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, 'ABC Biscuits', (50, 550), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    
    # Save test image
    cv2.imwrite("test_data/good.jpg", img)
    
    # Run pipeline
    pipeline = create_pipeline(text_det_thresh=0.1, text_det_box_thresh=0.1)
    result = pipeline.inspect_image(img, source_name="test_data/good.jpg")
    
    print("Inspection Result:")
    print(pipeline.to_json(result))