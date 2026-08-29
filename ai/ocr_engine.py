"""
OCR Engine module using PaddleOCR (PaddleX backend).

Provides a clean interface for running OCR on OpenCV images/NumPy arrays
and extracting text, confidence scores, and bounding boxes.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import cv2
import os

# Disable oneDNN (MKLDNN) to avoid Windows compatibility issues
os.environ['FLAGS_use_onednn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

import paddle
paddle.set_flags({'FLAGS_use_onednn': False})

from paddlex import create_pipeline


class OCREngine:
    """PaddleOCR wrapper for packaged commodity inspection."""

    def __init__(
        self,
        det_model_dir: Optional[str] = None,
        rec_model_dir: Optional[str] = None,
        use_doc_orientation_classify: bool = False,
        use_doc_unwarping: bool = False,
        use_textline_orientation: bool = False,
        device: str = 'cpu',
        text_det_thresh: float = 0.3,
        text_det_box_thresh: float = 0.5
    ):
        """
        Initialize PaddleOCR engine using PaddleX pipeline.

        Args:
            det_model_dir: Path to detection model directory (optional, uses default)
            rec_model_dir: Path to recognition model directory (optional, uses default)
            use_doc_orientation_classify: Enable document orientation classification
            use_doc_unwarping: Enable document unwarping
            use_textline_orientation: Enable text line orientation classification
            device: Device to use ('cpu' or 'gpu')
            text_det_thresh: Text detection threshold (lower = more sensitive)
            text_det_box_thresh: Text detection box threshold (lower = more sensitive)
        """
        self.device = device
        self.text_det_thresh = text_det_thresh
        self.text_det_box_thresh = text_det_box_thresh
        self.use_doc_orientation_classify = use_doc_orientation_classify
        self.use_doc_unwarping = use_doc_unwarping
        self.use_textline_orientation = use_textline_orientation
        
        # Build engine config to disable MKLDNN (oneDNN) on Windows
        engine_config = {
            'enable_mkldnn': False,
            'disable_mkldnn': True,
            'run_mode': 'paddle',
            'enable_new_ir': False,
            'delete_pass': ['mkldnn_pass']
        }

        self.pipeline = create_pipeline(
            'OCR',
            device=device,
            engine_config=engine_config
        )

    def _extract_from_result(self, result: Any) -> tuple:
        """Extract rec_texts, rec_scores, rec_polys from result (dict or object)."""
        if isinstance(result, dict):
            rec_texts = result.get('rec_texts', [])
            rec_scores = result.get('rec_scores', [])
            rec_polys = result.get('rec_polys', [])
        else:
            rec_texts = getattr(result, 'rec_texts', [])
            rec_scores = getattr(result, 'rec_scores', [])
            rec_polys = getattr(result, 'rec_polys', [])
        return rec_texts, rec_scores, rec_polys

    def run_ocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run OCR on an OpenCV image.

        Args:
            image: OpenCV image (numpy array, BGR format)

        Returns:
            List of dicts with keys: text, confidence, box
            box format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        if image is None or image.size == 0:
            return []

        # PaddleX expects RGB, OpenCV uses BGR
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        try:
            # Predict returns a generator
            results = list(self.pipeline.predict(
                image_rgb,
                text_det_thresh=self.text_det_thresh,
                text_det_box_thresh=self.text_det_box_thresh,
                use_doc_orientation_classify=self.use_doc_orientation_classify,
                use_doc_unwarping=self.use_doc_unwarping,
                use_textline_orientation=self.use_textline_orientation
            ))
        except Exception as e:
            print(f"OCR error: {e}")
            return []

        if not results:
            return []

        # Extract results from the first (and only) result
        result = results[0]
        
        structured_results = []
        
        # Get recognized texts, scores, and polygons
        rec_texts, rec_scores, rec_polys = self._extract_from_result(result)
        
        for i, text in enumerate(rec_texts):
            confidence = float(rec_scores[i]) if i < len(rec_scores) else 0.0
            
            # Convert polygon to box format [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            if i < len(rec_polys):
                poly = rec_polys[i]
                # poly is array of shape (4, 2) or similar
                box_list = [[int(p[0]), int(p[1])] for p in poly]
            else:
                box_list = []
            
            structured_results.append({
                "text": text,
                "confidence": confidence,
                "box": box_list
            })

        return structured_results


def create_ocr_engine(
    use_gpu: bool = False,
    det_model_dir: Optional[str] = None,
    rec_model_dir: Optional[str] = None,
    text_det_thresh: float = 0.3,
    text_det_box_thresh: float = 0.5
) -> OCREngine:
    """Factory function to create OCR engine."""
    device = 'gpu' if use_gpu else 'cpu'
    return OCREngine(
        det_model_dir=det_model_dir,
        rec_model_dir=rec_model_dir,
        device=device,
        text_det_thresh=text_det_thresh,
        text_det_box_thresh=text_det_box_thresh
    )


if __name__ == "__main__":
    # Quick test
    engine = create_ocr_engine()
    print("OCR Engine initialized successfully")
    print(f"PaddleOCR version: 3.7.0 (PaddleX backend)")