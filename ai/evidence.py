"""
Evidence Image module.

Draws bounding boxes on images for OCR results and extracted fields.
Saves annotated images to evidence/ folder.
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional


def draw_ocr_evidence(
    image: np.ndarray,
    ocr_results: List[Dict[str, Any]],
    output_path: str,
    color: tuple = (0, 255, 0),
    thickness: int = 2
) -> bool:
    """
    Draw OCR bounding boxes on image.
    
    Args:
        image: OpenCV image (BGR)
        ocr_results: List of OCR results with 'text', 'confidence', 'box'
        output_path: Path to save annotated image
        color: Box color (BGR)
        thickness: Line thickness
        
    Returns:
        True if saved successfully
    """
    if image is None or image.size == 0:
        return False
    
    annotated = image.copy()
    
    for item in ocr_results:
        box = item.get('box', [])
        text = item.get('text', '')
        confidence = item.get('confidence', 0.0)
        
        if not box or len(box) < 4:
            continue
        
        # Convert box to numpy array for cv2.polylines
        pts = np.array(box, dtype=np.int32)
        pts = pts.reshape((-1, 1, 2))
        
        # Draw polygon
        cv2.polylines(annotated, [pts], True, color, thickness)
        
        # Draw text label
        if text:
            # Position label at top-left of box
            x, y = box[0]
            label = f"{text} ({confidence:.2f})"
            cv2.putText(
                annotated, label, (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1
            )
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    return cv2.imwrite(output_path, annotated)


def draw_field_evidence(
    image: np.ndarray,
    fields: Dict[str, Any],
    output_path: str,
    color_map: Optional[Dict[str, tuple]] = None,
    thickness: int = 3
) -> bool:
    """
    Draw field bounding boxes on image with field names.
    
    Args:
        image: OpenCV image (BGR)
        fields: Dict of extracted fields with 'box', 'value', 'confidence'
        output_path: Path to save annotated image
        color_map: Optional dict mapping field names to colors
        thickness: Line thickness
        
    Returns:
        True if saved successfully
    """
    if image is None or image.size == 0:
        return False
    
    # Default colors for different fields
    default_colors = {
        'product_name': (255, 0, 0),      # Blue
        'brand': (255, 0, 255),           # Magenta
        'mrp': (0, 255, 0),               # Green
        'net_quantity': (0, 255, 255),    # Yellow
        'manufacturer': (255, 128, 0),    # Orange
        'packer': (255, 128, 0),          # Orange
        'importer': (255, 128, 0),        # Orange
        'country_of_origin': (128, 0, 255), # Purple
        'manufacturing_date': (0, 128, 255),  # Light Blue
        'expiry_date': (0, 100, 255),         # Darker Blue
        'batch_number': (128, 255, 0),        # Lime Green
    }
    
    colors = color_map or default_colors
    
    annotated = image.copy()
    
    for field_name, field_data in fields.items():
        if field_data is None:
            continue
            
        box = field_data.get('box', [])
        value = field_data.get('value', '')
        confidence = field_data.get('confidence', 0.0)
        level = field_data.get('level', '')
        
        if not box or len(box) < 4:
            continue
        
        color = colors.get(field_name, (255, 255, 255))
        
        # Convert box to numpy array
        pts = np.array(box, dtype=np.int32)
        pts = pts.reshape((-1, 1, 2))
        
        # Draw polygon
        cv2.polylines(annotated, [pts], True, color, thickness)
        
        # Draw field label
        x, y = box[0]
        label = f"{field_name}: {value} ({confidence:.2f} {level})"
        cv2.putText(
            annotated, label, (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    return cv2.imwrite(output_path, annotated)


def save_evidence_image(
    image: np.ndarray,
    base_name: str,
    ocr_results: List[Dict[str, Any]] = None,
    fields: Dict[str, Any] = None,
    evidence_dir: str = "evidence"
) -> Dict[str, str]:
    """
    Save multiple evidence images.
    
    Args:
        image: Original image
        base_name: Base filename (without extension)
        ocr_results: OCR results for annotation
        fields: Extracted fields for annotation
        evidence_dir: Directory to save evidence images
        
    Returns:
        Dict with paths to saved images
    """
    os.makedirs(evidence_dir, exist_ok=True)
    saved = {}
    
    # Original image
    original_path = os.path.join(evidence_dir, f"{base_name}_original.jpg")
    cv2.imwrite(original_path, image)
    saved['original'] = original_path
    
    # OCR evidence
    if ocr_results:
        ocr_path = os.path.join(evidence_dir, f"{base_name}_ocr.jpg")
        if draw_ocr_evidence(image, ocr_results, ocr_path):
            saved['ocr'] = ocr_path
    
    # Field evidence
    if fields:
        field_path = os.path.join(evidence_dir, f"{base_name}_fields.jpg")
        if draw_field_evidence(image, fields, field_path):
            saved['fields'] = field_path
    
    return saved


if __name__ == "__main__":
    # Test with synthetic image
    import numpy as np
    
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    img[:] = (255, 255, 255)
    cv2.putText(img, 'MRP Rs. 50', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, 'Net Qty: 200 g', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    cv2.putText(img, 'ABC Biscuits', (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
    
    test_ocr = [
        {"text": "MRP Rs. 50", "confidence": 0.97, "box": [[50, 80], [250, 80], [250, 120], [50, 120]]},
        {"text": "Net Qty: 200 g", "confidence": 0.96, "box": [[50, 180], [350, 180], [350, 220], [50, 220]]},
        {"text": "ABC Biscuits", "confidence": 0.94, "box": [[50, 280], [300, 280], [300, 320], [50, 320]]},
    ]
    
    test_fields = {
        "mrp": {"value": "50", "confidence": 0.97, "level": "HIGH", "box": [[50, 80], [250, 80], [250, 120], [50, 120]]},
        "net_quantity": {"value": "200", "confidence": 0.96, "level": "HIGH", "unit": "g", "box": [[50, 180], [350, 180], [350, 220], [50, 220]]},
        "product_name": {"value": "ABC Biscuits", "confidence": 0.94, "level": "HIGH", "box": [[50, 280], [300, 280], [300, 320], [50, 320]]},
        "brand": {"value": "ABC", "confidence": 0.92, "level": "HIGH", "box": [[50, 250], [150, 250], [150, 270], [50, 270]]},
        "manufacturer": {"value": "ABC Foods Ltd", "confidence": 0.91, "level": "HIGH", "box": [[50, 320], [300, 320], [300, 340], [50, 340]]},
        "manufacturing_date": {"value": "27/11/25", "confidence": 0.93, "level": "HIGH", "box": [[50, 360], [180, 360], [180, 380], [50, 380]]},
        "expiry_date": {"value": "27/11/26", "confidence": 0.93, "level": "HIGH", "box": [[50, 400], [180, 400], [180, 420], [50, 420]]},
        "batch_number": {"value": "B12345", "confidence": 0.90, "level": "HIGH", "box": [[50, 440], [180, 440], [180, 460], [50, 460]]},
    }
    
    os.makedirs("evidence", exist_ok=True)
    
    # Test OCR evidence
    draw_ocr_evidence(img, test_ocr, "evidence/test_ocr.jpg")
    print("Saved OCR evidence")
    
    # Test field evidence
    draw_field_evidence(img, test_fields, "evidence/test_fields.jpg")
    print("Saved field evidence")
    
    # Test combined
    saved = save_evidence_image(img, "test_combined", test_ocr, test_fields)
    print(f"Saved: {saved}")