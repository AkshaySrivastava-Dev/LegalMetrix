"""
NVIDIA Nemotron OCR v2 API Client.

Replaces PaddleOCR with NVIDIA's hosted OCR API for faster inference.
Sends all images (front, back, side) in a single request.
"""

import os
import time
import base64
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import cv2
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

NVIDIA_OCR_ENDPOINT = "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2"
SOURCE_NAMES = ["front", "back", "side"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NVIDIAOCRConfig:
    api_key: str
    timeout: int = 60
    max_image_dimension: int = 2048
    jpeg_quality: int = 85


class NVIDIAOCRError(Exception):
    """Custom exception for NVIDIA OCR API errors."""
    pass


def _get_api_key() -> str:
    """Get NVIDIA API key from environment variable."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise NVIDIAOCRError("NVIDIA_API_KEY not set in environment")
    return api_key


def _resize_image_if_needed(image: np.ndarray, max_dimension: int) -> np.ndarray:
    """Resize image if it exceeds max dimension, preserving aspect ratio."""
    h, w = image.shape[:2]
    if max(h, w) <= max_dimension:
        return image
    
    scale = max_dimension / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _encode_image_to_base64(image: np.ndarray, jpeg_quality: int = 85) -> str:
    """Encode OpenCV image to base64 JPEG data URL."""
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if len(image.shape) == 3 else image
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    success, buffer = cv2.imencode('.jpg', image_rgb, encode_params)
    if not success:
        raise NVIDIAOCRError("Failed to encode image to JPEG")
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


def _prepare_images(images: List[np.ndarray], config: NVIDIAOCRConfig) -> List[str]:
    """Prepare images for NVIDIA OCR API: resize and encode to base64."""
    prepared = []
    for img in images:
        if img is None or img.size == 0:
            raise NVIDIAOCRError("Empty image provided")
        resized = _resize_image_if_needed(img, config.max_image_dimension)
        encoded = _encode_image_to_base64(resized, config.jpeg_quality)
        prepared.append(encoded)
    return prepared


def _build_nvidia_request(image_data_urls: List[str]) -> Dict[str, Any]:
    """Build NVIDIA OCR API request payload."""
    return {
        "input": [
            {"type": "image_url", "url": url}
            for url in image_data_urls
        ]
    }


def _parse_nvidia_response(
    response: Dict[str, Any],
    valid_images: List[np.ndarray],
    num_images: int
) -> List[List[Dict[str, Any]]]:
    """
    Parse NVIDIA OCR response into normalized detections list for each image.
    
    Response format from NVIDIA Nemotron OCR v2:
    {
      "data": [
        {
          "index": 0,
          "text_detections": [
            {
              "text_prediction": {
                "text": "...",
                "confidence": 0.95
              },
              "bounding_box": {
                "points": [{"x": 0.1, "y": 0.2}, ...]
              }
            }
          ]
        }
      ]
    }
    """
    results: List[List[Dict[str, Any]]] = [[] for _ in range(num_images)]
    
    try:
        data_list = response.get("data", [])
        for item in data_list:
            idx = item.get("index", 0)
            if idx >= num_images:
                continue
            
            img = valid_images[idx] if idx < len(valid_images) else None
            h, w = img.shape[:2] if img is not None else (1, 1)
            
            detections = []
            for det in item.get("text_detections", []):
                pred = det.get("text_prediction", {})
                text = pred.get("text", "").strip()
                confidence = float(pred.get("confidence", 0.0))
                
                points = det.get("bounding_box", {}).get("points", [])
                box = []
                for pt in points:
                    px = pt.get("x", 0.0)
                    py = pt.get("y", 0.0)
                    # Convert normalized coords [0, 1] to pixel coords
                    if px <= 1.0 and py <= 1.0 and w > 1 and h > 1:
                        box.append([int(round(px * w)), int(round(py * h))])
                    else:
                        box.append([int(round(px)), int(round(py))])
                
                if text:
                    detections.append({
                        "text": text,
                        "confidence": confidence,
                        "box": box
                    })
            results[idx] = detections
            
    except Exception as e:
        logger.error(f"Error parsing NVIDIA OCR response: {e}")
        
    return results


class NVIDIAOCREngine:
    """NVIDIA Nemotron OCR v2 Engine - drop-in replacement for PaddleOCR engine."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 60,
        max_image_dimension: int = 2048,
        jpeg_quality: int = 85
    ):
        self.config = NVIDIAOCRConfig(
            api_key=api_key or _get_api_key(),
            timeout=timeout,
            max_image_dimension=max_image_dimension,
            jpeg_quality=jpeg_quality
        )
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def run_ocr(self, image: np.ndarray, source_name: str = "front") -> List[Dict[str, Any]]:
        """
        Run OCR on a single image.
        Maintains compatibility with existing OCREngine.run_ocr interface.
        """
        return self.run_ocr_multi([image], [source_name])[0] if image is not None else []
    
    def run_ocr_multi(
        self,
        images: List[np.ndarray],
        source_names: List[str]
    ) -> List[List[Dict[str, Any]]]:
        """
        Run OCR on multiple images in a single API call.
        
        Args:
            images: List of OpenCV images (numpy arrays, BGR)
            source_names: List of source identifiers (e.g., ['front', 'back', 'side'])
            
        Returns:
            List of OCR results per image, each containing list of detections
        """
        if not images or not any(img is not None and img.size > 0 for img in images):
            return [[] for _ in images]
        
        valid_images = []
        valid_indices = []
        for i, img in enumerate(images):
            if img is not None and img.size > 0:
                valid_images.append(img)
                valid_indices.append(i)
        
        start_time = time.perf_counter()
        
        try:
            image_data_urls = _prepare_images(valid_images, self.config)
            prep_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"Image preparation: {prep_time:.1f} ms")
            
            request_payload = _build_nvidia_request(image_data_urls)
            
            api_start = time.perf_counter()
            response = self._session.post(
                NVIDIA_OCR_ENDPOINT,
                json=request_payload,
                timeout=self.config.timeout
            )
            api_time = (time.perf_counter() - api_start) * 1000
            logger.info(f"NVIDIA OCR request: {api_time:.1f} ms")
            
            if response.status_code == 401:
                raise NVIDIAOCRError("Invalid NVIDIA API key")
            elif response.status_code == 429:
                raise NVIDIAOCRError("NVIDIA OCR rate limit exceeded")
            elif response.status_code >= 500:
                raise NVIDIAOCRError(f"NVIDIA OCR service error: HTTP {response.status_code}")
            elif response.status_code >= 400:
                raise NVIDIAOCRError(f"NVIDIA OCR request failed: HTTP {response.status_code}")
            
            response_data = response.json()
            parsed_valid_results = _parse_nvidia_response(response_data, valid_images, len(valid_images))
            
            results = [[] for _ in images]
            for valid_idx, res in zip(valid_indices, parsed_valid_results):
                results[valid_idx] = res
            
            total_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"Total OCR time: {total_time:.1f} ms")
            
            return results
            
        except requests.Timeout:
            raise NVIDIAOCRError("NVIDIA OCR request timeout")
        except requests.ConnectionError:
            raise NVIDIAOCRError("NVIDIA OCR connection failed")
        except NVIDIAOCRError:
            raise
        except Exception as e:
            logger.error(f"NVIDIA OCR unexpected error: {e}")
            raise NVIDIAOCRError(f"OCR failed: {str(e)}")
    
    def close(self):
        """Close HTTP session."""
        self._session.close()


def create_nvidia_ocr_engine(
    api_key: Optional[str] = None,
    timeout: int = 60,
    max_image_dimension: int = 2048,
    jpeg_quality: int = 85
) -> NVIDIAOCREngine:
    """Factory function to create NVIDIA OCR engine."""
    return NVIDIAOCREngine(
        api_key=api_key,
        timeout=timeout,
        max_image_dimension=max_image_dimension,
        jpeg_quality=jpeg_quality
    )


if __name__ == "__main__":
    import sys
    
    try:
        engine = create_nvidia_ocr_engine()
        print("NVIDIA OCR Engine initialized successfully")
        print(f"Endpoint: {NVIDIA_OCR_ENDPOINT}")
    except NVIDIAOCRError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)