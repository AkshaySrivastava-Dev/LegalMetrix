"""
Image Quality Check module using OpenCV.

Provides field-aware checks for blur, brightness, resolution, and visibility.
"""

from typing import Dict, Any
import cv2
import numpy as np


# Thresholds
QUALITY_THRESHOLDS = {
    "min_width": 480,
    "min_height": 360,
    "min_blur_score": 25.0,       # Below 25 is severely blurred
    "good_blur_score": 55.0,      # Above 55 is crisp
    "min_brightness": 30.0,       # Mean pixel value (0-255)
    "max_brightness": 235.0,      # Mean pixel value (0-255)
    "min_edge_ratio": 0.0005,     # Ratio of edge pixels to total
    "max_edge_ratio": 0.6,        # Too many edges might indicate noise
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
        Dict with status (GOOD/ACCEPTABLE/BAD), reasons, and metrics
    """
    if image is None or image.size == 0:
        return {
            "status": "BAD",
            "reasons": ["Invalid image"],
            "metrics": {}
        }
    
    reasons = []
    warnings = []
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
        reasons.append("Image severely blurry")
    elif blur_score < QUALITY_THRESHOLDS["good_blur_score"]:
        warnings.append("Slight blur on fine text")
    
    # Brightness
    brightness = check_brightness(image)
    metrics["brightness"] = round(brightness, 2)
    
    if brightness < QUALITY_THRESHOLDS["min_brightness"]:
        reasons.append("Image too dark")
    elif brightness > QUALITY_THRESHOLDS["max_brightness"]:
        reasons.append("Image too bright")
    
    # Edge ratio
    edge_ratio = check_edge_ratio(image)
    metrics["edge_ratio"] = round(edge_ratio, 4)
    
    if edge_ratio < QUALITY_THRESHOLDS["min_edge_ratio"]:
        reasons.append("Label not clearly visible")
    
    if len(reasons) > 0:
        status = "BAD"
    elif len(warnings) > 0:
        status = "ACCEPTABLE"
    else:
        status = "GOOD"
    
    all_notes = reasons + warnings
    
    return {
        "status": status,
        "reasons": all_notes,
        "issues": all_notes,
        "metrics": metrics
    }

