"""
AI Service Adapter.
Acts as a clean wrapper for OCR, Computer Vision, and Product Extraction models.
Uses mock mode when external AI engines are not yet integrated.
"""

import os
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from ..models.schemas import AIAnalysisResult

logger = logging.getLogger("legal_metrology.ai_service")

# Realistic sample mock datasets for demo purposes
MOCK_PRODUCTS = [
    {
        "product_name": "Krunchy Treat Butter Cookies",
        "brand": "Britannica Foods",
        "category": "packaged_food",
        "variant": "Butter Delite 150g",
        "mrp": "₹45.00 (incl. of all taxes)",
        "net_quantity": "150 g",
        "manufacturer": "Britannica Industries Ltd., Plot 12, Industrial Area, Sector 62, Noida - 201301, UP, India",
        "confidence": 0.94,
        "raw_text": "BRITANNICA KRUNCHY TREAT BUTTER COOKIES Net Qty: 150g MRP: Rs. 45.00 incl. of all taxes Mfd by: Britannica Industries Ltd. Noida 201301 UP Mfg Date: 07/2026 Use by: 6 months from packaging Consumer Care: care@britannica.com / 1800-111-222",
        "evidence": {
            "mrp_bbox": [120, 340, 260, 370],
            "net_qty_bbox": [120, 380, 240, 410],
            "manufacturer_bbox": [120, 420, 500, 470],
        },
    },
    {
        "product_name": "Pure Gold Refined Mustard Oil",
        "brand": "Dhara Agro",
        "category": "edible_oil",
        "variant": "Pouch 1L",
        "mrp": "₹165.00",
        "net_quantity": "1 L / 910 g",
        "manufacturer": "Dhara Agro Processing Pvt Ltd, Phase II, RIICO, Jaipur - 302022, Rajasthan, India",
        "confidence": 0.91,
        "raw_text": "DHARA AGRO PURE GOLD MUSTARD OIL Net Content: 1 Litre MRP Rs 165 (Incl. all taxes) Packed at: Dhara Agro Processing, RIICO Jaipur 302022 Customer Support: 1800-222-3333 Best Before: 9 Months",
        "evidence": {
            "mrp_bbox": [95, 290, 210, 320],
            "net_qty_bbox": [95, 330, 220, 360],
            "manufacturer_bbox": [95, 370, 450, 410],
        },
    },
    {
        "product_name": "Sparkle Active Detergent Powder",
        "brand": "CleanMaster",
        "category": "household_cleaning",
        "variant": "Lemon Fresh 1kg",
        "mrp": "₹120.00 (incl. of all taxes)",
        "net_quantity": "1 kg",
        "manufacturer": "CleanMaster Homecare Corp, GIDC Estate, Vatva, Ahmedabad - 382445, Gujarat",
        "confidence": 0.88,
        "raw_text": "CLEANMASTER SPARKLE ACTIVE DETERGENT POWDER 1kg Net Wt. MRP: Rs 120.00 Mfd by CleanMaster Homecare Corp Ahmedabad 382445 For Consumer Feedback: customercare@cleanmaster.in",
        "evidence": {
            "mrp_bbox": [150, 400, 300, 440],
            "net_qty_bbox": [150, 450, 270, 480],
            "manufacturer_bbox": [150, 490, 520, 540],
        },
    },
]


def is_mock_ai_enabled() -> bool:
    """Returns True if mock AI mode is enabled via environment variables."""
    return os.getenv("MOCK_AI", "true").strip().lower() in ("true", "1", "yes")


async def analyze_image(file_path: str) -> AIAnalysisResult:
    """
    Analyzes an uploaded packaged commodity image to extract key Legal Metrology declarations.
    Calls external AI engine if integrated, or falls back to realistic mock extraction.
    """
    logger.info(f"AI Service: Processing image at '{file_path}' (mock_mode={is_mock_ai_enabled()})")

    if not is_mock_ai_enabled():
        # Hook for external AI Module:
        try:
            # e.g., from ai_module import extract_declarations
            # result = await extract_declarations(file_path)
            # return AIAnalysisResult(**result)
            pass
        except Exception as e:
            logger.error(f"External AI module execution failed: {e}. Falling back to adapter mock.")

    # Select mock item based on filename hash for deterministic demo behavior
    seed = sum(ord(c) for c in Path(file_path).name)
    sample = MOCK_PRODUCTS[seed % len(MOCK_PRODUCTS)]

    return AIAnalysisResult(
        product_name=sample["product_name"],
        brand=sample["brand"],
        category=sample["category"],
        variant=sample["variant"],
        mrp=sample["mrp"],
        net_quantity=sample["net_quantity"],
        manufacturer=sample["manufacturer"],
        confidence=sample["confidence"],
        raw_text=sample["raw_text"],
        evidence=sample["evidence"],
        source="image",
    )


async def analyze_video(file_path: str) -> AIAnalysisResult:
    """
    Processes a 360-degree video scan of a package.
    In production, samples frames every ~0.5s, aggregates detections across surfaces, and fuses results.
    """
    logger.info(f"AI Service: Processing 360 video at '{file_path}' (mock_mode={is_mock_ai_enabled()})")

    if not is_mock_ai_enabled():
        try:
            # Hook for external CV Video Pipeline
            # from ai_module.video import process_360_video
            # result = await process_360_video(file_path)
            # return AIAnalysisResult(**result)
            pass
        except Exception as e:
            logger.error(f"External Video AI module failed: {e}. Falling back to adapter mock.")

    # High confidence aggregated result for multi-angle capture
    sample = MOCK_PRODUCTS[0]
    return AIAnalysisResult(
        product_name=sample["product_name"],
        brand=sample["brand"],
        category=sample["category"],
        variant=sample["variant"],
        mrp=sample["mrp"],
        net_quantity=sample["net_quantity"],
        manufacturer=sample["manufacturer"],
        confidence=0.97,  # Video frame fusion offers higher detection confidence
        raw_text=f"[360 Multi-Frame Aggregation] {sample['raw_text']}",
        evidence={
            "angles_scanned": 12,
            "front_panel_confidence": 0.98,
            "back_panel_confidence": 0.96,
            "side_panels_confidence": 0.95,
        },
        source="video_360",
    )
