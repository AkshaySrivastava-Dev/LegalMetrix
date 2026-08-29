"""
Image Quality Check module using OpenCV.

Provides heuristic checks for blur, brightness, resolution, and visibility.
"""

from typing import Dict, Any
import cv2
import numpy as np


# Thresholds - easily modifiable in one place
QUALITY_THRESHOLDS = {
    "min_width": 640,
    "min_height": 480,
    "min_blur_score": 50.0,       # Laplacian variance threshold
    "max_blur_score": 5000.0,     # Very high blur score might indicate issues
    "min_brightness": 40.0,       # Mean pixel value (0-255)
    "max_brightness": 220.0,      # Mean pixel value (0-255)
    "min_edge_ratio": 0.001,      # Ratio of edge pixels to total (lowered for text)
    "max_edge_ratio": 0.5,        # Too many edges might indicate noise
}


def check_blur(image: np.ndarray) -> float:
    """
    Compute blur score using Laplacian variance.
    Higher score = sharper image.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def check_brightness(image: np.ndarray) -> float:
    """
    Compute mean brightness of the image.
    Returns mean pixel value (0-255).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    return float(np.mean(gray))


def check_resolution(image: np.ndarray) -> tuple:
    """
    Check image resolution.
    Returns (width, height).
    """
    h, w = image.shape[:2]
    return w, h


def check_edge_ratio(image: np.ndarray) -> float:
    """
    Compute ratio of edge pixels to total pixels.
    Uses Canny edge detection.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    edges = cv2.Canny(gray, 50, 150)
    edge_pixels = np.count_nonzero(edges)
    total_pixels = gray.size
    return float(edge_pixels) / float(total_pixels)


def check_image_quality(image: np.ndarray) -> Dict[str, Any]:
    """
    Check image quality for OCR suitability.
    
    Args:
        image: OpenCV image (numpy array, BGR format)
        
    Returns:
        Dict with status, reasons, and metrics
    """
    if image is None or image.size == 0:
        return {
            "status": "BAD",
            "reasons": ["Invalid image"],
            "metrics": {}
        }
    
    reasons = []
    metrics = {}
    
    # Resolution
    width, height = check_resolution(image)
    metrics["width"] = width
    metrics["height"] = height
    
    if width < QUALITY_THRESHOLDS["min_width"] or height < QUALITY_THRESHOLDS["min_height"]:
        reasons.append("Move closer / image resolution too low")
    
    # Blur
    blur_score = check_blur(image)
    metrics["blur_score"] = round(blur_score, 2)
    
    if blur_score < QUALITY_THRESHOLDS["min_blur_score"]:
        reasons.append("Image blurry")
    
    # Brightness
    brightness = check_brightness(image)
    metrics["brightness"] = round(brightness, 2)
    
    if brightness < QUALITY_THRESHOLDS["min_brightness"]:
        reasons.append("Image too dark")
    elif brightness > QUALITY_THRESHOLDS["max_brightness"]:
        reasons.append("Image too bright")
    
    # Edge ratio (basic visibility check)
    edge_ratio = check_edge_ratio(image)
    metrics["edge_ratio"] = round(edge_ratio, 4)
    
    if edge_ratio < QUALITY_THRESHOLDS["min_edge_ratio"]:
        reasons.append("Label not clearly visible")
    elif edge_ratio > QUALITY_THRESHOLDS["max_edge_ratio"]:
        reasons.append("Image too noisy")
    
    status = "GOOD" if len(reasons) == 0 else "BAD"
    
    return {
        "status": status,
        "reasons": reasons,
        "metrics": metrics
    }


if __name__ == "__main__":
    # Quick test
    import numpy as np
    
    # Good image
    good_img = np.zeros((480, 640, 3), dtype=np.uint8)
    good_img[:] = (200, 200, 200)
    cv2.putText(good_img, 'Test Text', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    
    result = check_image_quality(good_img)
    print("Good image:", result)
    
    # Blurry image
    blurry_img = cv2.GaussianBlur(good_img, (21, 21), 0)
    result = check_image_quality(blurry_img)
    print("Blurry image:", result)
    
    # Dark image
    dark_img = np.zeros((480, 640, 3), dtype=np.uint8)
    dark_img[:] = (20, 20, 20)
    result = check_image_quality(dark_img)
    print("Dark image:", result)
    
    # Bright image
    bright_img = np.zeros((480, 640, 3), dtype=np.uint8)
    bright_img[:] = (240, 240, 240)
    result = check_image_quality(bright_img)
    print("Bright image:", result)