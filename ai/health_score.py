"""
Centralized Configurable Health Score Engine.

Calculates demonstration health scores (0-10) for packaged products.

Features:
- Configured demo scores for known brands:
  - Pepsi: 5 / 10 -> NOT_HEALTHY (<= 7)
  - Maaza: 6 / 10 -> NOT_HEALTHY (<= 7)
  - Too Yumm / Chips: 8 / 10 -> HEALTHY (> 7)
  - Badam Milk: 7 / 10 -> NOT_HEALTHY (<= 7)
- Random demo score generation (0-10) for unknown/unconfigured products
- Strict threshold: score > 7 is HEALTHY, score <= 7 is NOT_HEALTHY
- Modular design extensible to verified nutritional datasets or ML models
"""

import re
import random
from typing import Dict, Any, Optional

HEALTH_SCORES_REGISTRY: Dict[str, float] = {
    "pepsi": 5.0,
    "maaza": 6.0,
    "too_yumm": 8.0,
    "badam_milk": 7.0
}


def _normalize_text(text: str) -> str:
    """Normalize text for consistent brand/product matching."""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def evaluate_health_score(
    brand: Optional[str] = None,
    product_name: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates or generates a prototype health score (0-10) for a packaged commodity.

    Args:
        brand: Detected or canonical brand name
        product_name: Detected product name
        fields: Full dictionary of extracted fields

    Returns:
        Dict with keys:
            - score: float (0.0 - 10.0)
            - out_of: 10
            - status: "HEALTHY" (if score > 7) | "NOT_HEALTHY" (if score <= 7)
            - source: "demo_product_rule" | "demo_random"
            - label: "Demo Health Score"
    """
    candidates = []
    if brand:
        candidates.append(str(brand))
    if product_name:
        candidates.append(str(product_name))
    if fields:
        for k in ["brand", "product_name"]:
            val = fields.get(k)
            if isinstance(val, dict):
                v = val.get("value")
                if v and str(v) not in candidates:
                    candidates.append(str(v))
            elif isinstance(val, str) and val not in candidates:
                candidates.append(val)

    combined_text = " ".join(candidates)
    norm = _normalize_text(combined_text)

    # 1. Match Pepsi -> 5.0
    pepsi_tokens = ["pepsi", "pepsl", "peps1", "pepci", "pepsico"]
    for token in pepsi_tokens:
        if token in norm:
            score = HEALTH_SCORES_REGISTRY["pepsi"]
            return {
                "score": score,
                "out_of": 10,
                "status": "HEALTHY" if score > 7.0 else "NOT_HEALTHY",
                "source": "demo_product_rule",
                "label": "Demo Health Score"
            }

    # 2. Match Maaza / Mazza -> 6.0
    maaza_tokens = ["maaza", "mazza", "maza", "merea", "maazza"]
    for token in maaza_tokens:
        if token in norm:
            score = HEALTH_SCORES_REGISTRY["maaza"]
            return {
                "score": score,
                "out_of": 10,
                "status": "HEALTHY" if score > 7.0 else "NOT_HEALTHY",
                "source": "demo_product_rule",
                "label": "Demo Health Score"
            }

    # 3. Match Too Yumm / Chips -> 8.0
    too_yumm_tokens = [
        "too yumm", "tooyumm", "asc chips", "american style",
        "cream and onion", "cream and onion chips", "guiltfree industries"
    ]
    for token in too_yumm_tokens:
        if token in norm:
            score = HEALTH_SCORES_REGISTRY["too_yumm"]
            return {
                "score": score,
                "out_of": 10,
                "status": "HEALTHY" if score > 7.0 else "NOT_HEALTHY",
                "source": "demo_product_rule",
                "label": "Demo Health Score"
            }

    if brand and _normalize_text(brand) in ["too yumm", "tooyumm"]:
        score = HEALTH_SCORES_REGISTRY["too_yumm"]
        return {
            "score": score,
            "out_of": 10,
            "status": "HEALTHY" if score > 7.0 else "NOT_HEALTHY",
            "source": "demo_product_rule",
            "label": "Demo Health Score"
        }

    # 4. Match Badam Milk / Badamm -> 7.0
    badam_tokens = ["badam milk", "badamm", "badamml", "badamm milk", "jersey badam"]
    for token in badam_tokens:
        if token in norm:
            score = HEALTH_SCORES_REGISTRY["badam_milk"]
            return {
                "score": score,
                "out_of": 10,
                "status": "HEALTHY" if score > 7.0 else "NOT_HEALTHY",
                "source": "demo_product_rule",
                "label": "Demo Health Score"
            }

    # 5. Unknown Product: Generate Demo Random Score between 2.0 and 9.5
    random_score = round(random.uniform(2.0, 9.5), 1)
    return {
        "score": random_score,
        "out_of": 10,
        "status": "HEALTHY" if random_score > 7.0 else "NOT_HEALTHY",
        "source": "demo_random",
        "label": "Demo Health Score"
    }
