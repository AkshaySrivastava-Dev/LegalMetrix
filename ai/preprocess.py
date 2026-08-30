"""
Image Preprocessing and Barcode Detection Module for LegalMetrix AI Pipeline.

Provides image enhancement (CLAHE contrast, sharpening, dot-matrix binarization)
and barcode detection for packaged commodity labels.
"""

from typing import Optional, Dict, Any
import cv2
import numpy as np


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    to improve OCR on low-contrast or unevenly lit package surfaces.
    """
    if image is None or image.size == 0:
        return image

    if len(image.shape) == 3 and image.shape[2] == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    elif len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    return image


def sharpen_image(image: np.ndarray) -> np.ndarray:
    """
    Apply unsharp masking to enhance fine text, batch codes, and small dates.
    """
    if image is None or image.size == 0:
        return image

    gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
    sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    return sharpened


def enhance_dot_matrix(image: np.ndarray) -> np.ndarray:
    """
    Specialized preprocessor for dot-matrix printed dates and batch numbers.
    Uses morphological closing to connect isolated ink dots.
    """
    if image is None or image.size == 0:
        return image

    if len(image.shape) == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 4
    )

    # Morphological closing with small elliptical kernel to connect ink dots
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Invert back to black text on white background
    result = cv2.bitwise_not(closed)
    return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)


def detect_barcode(image: np.ndarray) -> Optional[Dict[str, Any]]:
    """
    Detect and decode 1D/2D barcodes (EAN-13, UPC, QR) from packaging image.
    
    Returns:
        Dict with 'data', 'type', and 'box' if barcode detected, else None.
    """
    if image is None or image.size == 0:
        return None

    try:
        detector = cv2.barcode.BarcodeDetector()
        ok, decoded_info, decoded_type, corners = detector.detectAndDecode(image)
        if ok and decoded_info:
            for info, b_type, corner in zip(decoded_info, decoded_type, corners):
                if info.strip():
                    box = [[int(pt[0]), int(pt[1])] for pt in corner]
                    return {
                        "data": info.strip(),
                        "type": str(b_type),
                        "box": box
                    }
    except Exception:
        pass
    return None


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Standard preprocessing pipeline combining contrast enhancement and sharpening.
    """
    enhanced = enhance_contrast(image)
    sharpened = sharpen_image(enhanced)
    return sharpened
