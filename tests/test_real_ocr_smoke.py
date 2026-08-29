"""
Developer Smoke-Test Utility for Real OCR -> Compliance Flow.

Usage:
    python tests/test_real_ocr_smoke.py [path/to/image.jpg]

Runs real PaddleOCR on a sample package image, extracts Legal Metrology declarations,
and evaluates compliance deterministically without mocking.
"""

import json
import os
import sys
import cv2
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from ai.pipeline import InspectionAI
from api.routes import map_ai_fields_to_compliance
from rules.engine import evaluate_compliance


def run_ocr_smoke_test(image_path: str = "test_data/test_image.jpg") -> dict:
    print("=" * 60)
    print("LEGALMETRIX REAL OCR & COMPLIANCE SMOKE TEST")
    print("=" * 60)
    print(f"Target image: {image_path}")

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")

    print(f"Image dimensions: {img.shape[1]}x{img.shape[0]} px")
    print("-" * 60)

    # 1. Initialize Pipeline
    print("[1/4] Initializing PaddleOCR pipeline...")
    pipeline = InspectionAI(save_evidence=False)

    # 2. Run Image Inspection
    print("[2/4] Running OCR & field extraction...")
    ai_result = pipeline.inspect_image(img, source_name=os.path.basename(image_path))

    # Print Detected Text
    raw_ocr = ai_result.get("raw_ocr", [])
    print(f"\n--- DETECTED OCR LINES ({len(raw_ocr)} lines found) ---")
    for idx, item in enumerate(raw_ocr, 1):
        text = item.get("text", "")
        conf = item.get("confidence", 0.0)
        box = item.get("box", [])
        print(f"  {idx:02d}. [{conf*100:.1f}%] \"{text}\" | Box: {box}")

    # Print Extracted Fields
    ai_fields = ai_result.get("fields", {})
    detected_cat = ai_result.get("category", "unknown")
    quality = ai_result.get("quality", {})
    print(f"\n--- IMAGE QUALITY & CLASSIFICATION ---")
    print(f"  Quality Status: {quality.get('status')} (Score: {quality.get('score', 'N/A')})")
    print(f"  Auto-detected Category: '{detected_cat}'")

    print(f"\n--- EXTRACTED FIELDS ---")
    for field_name, f_data in ai_fields.items():
        if f_data:
            val = f_data.get("value")
            conf = f_data.get("confidence", 0.0)
            lvl = f_data.get("level", "N/A")
            unit = f_data.get("unit", "")
            unit_str = f" {unit}" if unit else ""
            print(f"  • {field_name:20s}: '{val}{unit_str}' (Conf: {conf*100:.1f}%, Level: {lvl})")
        else:
            print(f"  • {field_name:20s}: [NOT DETECTED]")

    # 3. Map to Compliance Input
    print("\n[3/4] Mapping AI fields to Legal Metrology compliance format...")
    target_category = detected_cat if detected_cat != "unknown" else "food"
    extracted, confidences, evidences = map_ai_fields_to_compliance(
        ai_fields, source_name=os.path.basename(image_path)
    )

    # 4. Evaluate Compliance
    print(f"[4/4] Evaluating compliance against '{target_category}' rules...")
    eval_result = evaluate_compliance(
        category=target_category,
        extracted_data=extracted,
        confidence_data=confidences,
        evidence_data=evidences,
    )

    print("\n" + "=" * 60)
    print(f"FINAL COMPLIANCE STATUS : {eval_result['overall_status']}")
    print(f"SUMMARY                 : {eval_result['summary']}")
    print(f"RULES EVALUATED         : Total={eval_result['total_rules_evaluated']}, "
          f"Passed={eval_result['passed_count']}, "
          f"Failed={eval_result['failed_count']}, "
          f"Uncertain={eval_result['uncertain_count']}")
    print("=" * 60)

    print("\n--- FINDINGS ---")
    for finding in eval_result.get("findings", []):
        res = finding.get("result", "")
        status_symbol = "✓ PASS" if res == "PASS" else ("✗ FAIL" if res == "FAIL" else "? REVIEW")
        print(f"  [{status_symbol:8s}] {finding['rule_id']} - {finding['field']}: {finding['reason']}")

    if eval_result.get("manual_reviews"):
        print("\n--- MANUAL REVIEWS REQUIRED ---")
        for mr in eval_result["manual_reviews"]:
            print(f"  [REVIEW] Field: {mr['field']} | AI Value: '{mr['ai_value']}' | Confidence: {mr['confidence']}%")

    print("\nSmoke test completed successfully!")
    return eval_result


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "test_data/test_image.jpg"
    run_ocr_smoke_test(target)
