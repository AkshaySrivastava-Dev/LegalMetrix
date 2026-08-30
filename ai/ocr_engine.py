"""
Unified OCR Engine Module for LegalMetrix AI Pipeline.

Provides a unified interface for running OCR on OpenCV images / NumPy arrays
with flexible backend support:
- NVIDIA Nemotron OCR (Cloud high-accuracy model via NVIDIA API)
- PaddleOCR / PaddleX (Local model)
- Heuristic fallback engine for local/offline testing
"""

import os
from typing import List, Dict, Any, Optional
import numpy as np
import cv2

from ai.preprocess import preprocess_for_ocr


class OCREngine:
    """Unified OCR Engine wrapper for packaged commodity inspection."""

    def __init__(
        self,
        backend: str = "auto",
        device: str = "cpu",
        text_det_thresh: float = 0.3,
        text_det_box_thresh: float = 0.5,
        api_key: Optional[str] = None
    ):
        """
        Initialize OCR Engine.
        
        Args:
            backend: 'auto', 'nvidia', or 'paddle'
            device: 'cpu' or 'gpu'
            text_det_thresh: Detection threshold
            text_det_box_thresh: Box threshold
            api_key: Optional NVIDIA API key
        """
        self.device = device
        self.text_det_thresh = text_det_thresh
        self.text_det_box_thresh = text_det_box_thresh
        self.backend = backend
        self._engine = None
        self._backend_type = "mock"

        # Determine backend
        nvidia_key = api_key
        if not nvidia_key:
            try:
                from ai.nvidia_ocr import _get_api_key
                nvidia_key = _get_api_key()
            except Exception:
                nvidia_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_OCR_API_KEY")
        
        if backend in ("auto", "nvidia") and nvidia_key:
            try:
                from ai.nvidia_ocr import NVIDIAOCREngine
                self._engine = NVIDIAOCREngine(api_key=nvidia_key)
                self._backend_type = "nvidia"
            except Exception as e:
                print(f"[OCREngine] NVIDIA OCR init error: {e}")

        if self._engine is None and backend == "paddle":
            try:
                # Lazy import paddle
                os.environ['FLAGS_use_onednn'] = '0'
                os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
                import paddle
                paddle.set_flags({'FLAGS_use_onednn': False})
                from paddlex import create_pipeline
                
                engine_config = {
                    'enable_mkldnn': False,
                    'disable_mkldnn': True,
                    'run_mode': 'paddle',
                    'enable_new_ir': False,
                    'delete_pass': ['mkldnn_pass']
                }
                self._engine = create_pipeline(
                    'OCR',
                    device=device,
                    engine_config=engine_config
                )
                self._backend_type = "paddle"
            except Exception as e:
                print(f"[OCREngine] PaddleOCR not available: {e}")

        if self._engine is None:
            # Heuristic fallback engine
            self._backend_type = "fallback"

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

        # Run with NVIDIA backend
        if self._backend_type == "nvidia" and hasattr(self._engine, "run_ocr"):
            return self._engine.run_ocr(image)

        # Run with Paddle backend
        if self._backend_type == "paddle" and self._engine is not None:
            if len(image.shape) == 3 and image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image

            try:
                results = list(self._engine.predict(
                    image_rgb,
                    text_det_thresh=self.text_det_thresh,
                    text_det_box_thresh=self.text_det_box_thresh
                ))
            except Exception as e:
                print(f"Paddle OCR error: {e}")
                return []

            if not results:
                return []

            result = results[0]
            if isinstance(result, dict):
                rec_texts = result.get('rec_texts', [])
                rec_scores = result.get('rec_scores', [])
                rec_polys = result.get('rec_polys', [])
            else:
                rec_texts = getattr(result, 'rec_texts', [])
                rec_scores = getattr(result, 'rec_scores', [])
                rec_polys = getattr(result, 'rec_polys', [])

            structured = []
            for i, text in enumerate(rec_texts):
                confidence = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                if i < len(rec_polys):
                    poly = rec_polys[i]
                    box_list = [[int(p[0]), int(p[1])] for p in poly]
                else:
                    box_list = []
                structured.append({
                    "text": text,
                    "confidence": confidence,
                    "box": box_list
                })
            return structured

        # Fallback for images without active heavy model
        return []


def create_ocr_engine(
    use_gpu: bool = False,
    backend: str = "auto",
    det_model_dir: Optional[str] = None,
    rec_model_dir: Optional[str] = None,
    text_det_thresh: float = 0.3,
    text_det_box_thresh: float = 0.5,
    api_key: Optional[str] = None
) -> OCREngine:
    """Factory function to create OCR engine."""
    device = 'gpu' if use_gpu else 'cpu'
    return OCREngine(
        backend=backend,
        device=device,
        text_det_thresh=text_det_thresh,
        text_det_box_thresh=text_det_box_thresh,
        api_key=api_key
    )
