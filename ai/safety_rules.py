"""
Centralized Configurable Product Safety Rules Engine.

Evaluates configured product safety rules/alerts based on normalized brand and product identification.

Features:
- Configured Demo Safety Rules for known products (Maaza, Pepsi, Too Yumm, Badam Milk)
- Modular design so 'configured_demo_rule' can easily be swapped with verified authority sources
- Strictly independent from Legal Metrology compliance rules
- Clear provenance logging
"""

import re
from typing import Dict, Any, Optional


SAFETY_RULES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "maaza": {
        "status": "ALERT",
        "message": "Do not consume — product flagged by configured demo safety rule.",
        "source": "configured_demo_rule",
        "rule_id": "SAFETY-DEMO-MAAZA"
    },
    "pepsi": {
        "status": "ALERT",
        "message": "Do not consume — product flagged by configured demo safety rule.",
        "source": "configured_demo_rule",
        "rule_id": "SAFETY-DEMO-PEPSI"
    },
    "too_yumm": {
        "status": "SAFE_STATUS",
        "message": "No safety alert identified by the configured demo rules.",
        "source": "configured_demo_rule",
        "rule_id": "SAFETY-DEMO-TOO-YUMM"
    },
    "badam_milk": {
        "status": "SAFE_STATUS",
        "message": "No safety alert identified by the configured demo rules.",
        "source": "configured_demo_rule",
        "rule_id": "SAFETY-DEMO-BADAM-MILK"
    }
}

DEFAULT_NO_RULE: Dict[str, Any] = {
    "status": "NO_RULE",
    "message": "No configured safety alert for this product.",
    "source": None,
    "rule_id": None
}


def _normalize_text(text: str) -> str:
    """Normalize text for consistent rule matching."""
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("&", "and")
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def evaluate_product_safety(
    brand: Optional[str] = None,
    product_name: Optional[str] = None,
    fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluates whether a configured safety alert applies to the identified product/brand.
    
    Args:
        brand: Detected or canonical brand name
        product_name: Detected product name
        fields: Full dictionary of extracted fields
        
    Returns:
        Dict with keys:
            - status: "ALERT" | "SAFE_STATUS" | "NO_RULE"
            - message: Descriptive status message
            - source: "configured_demo_rule" | None
            - rule_id: Rule identifier | None
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

    if not norm:
        return dict(DEFAULT_NO_RULE)

    # 1. Check Pepsi
    pepsi_tokens = ["pepsi", "pepsl", "peps1", "pepci", "pepsico"]
    for token in pepsi_tokens:
        if token in norm:
            return dict(SAFETY_RULES_REGISTRY["pepsi"])

    # 2. Check Maaza / Mazza
    maaza_tokens = ["maaza", "mazza", "maza", "merea", "maazza"]
    for token in maaza_tokens:
        if token in norm:
            return dict(SAFETY_RULES_REGISTRY["maaza"])

    # 3. Check Badam Milk / Badamm
    badam_tokens = ["badam milk", "badamm", "badamml", "badamm milk", "jersey badam"]
    for token in badam_tokens:
        if token in norm:
            return dict(SAFETY_RULES_REGISTRY["badam_milk"])

    # 4. Check Too Yumm / Chips
    too_yumm_tokens = [
        "too yumm", "tooyumm", "asc chips", "american style",
        "cream and onion", "cream and onion chips", "guiltfree industries"
    ]
    for token in too_yumm_tokens:
        if token in norm:
            return dict(SAFETY_RULES_REGISTRY["too_yumm"])

    # Exact token match for "chips" if it was identified as Too Yumm brand
    if brand and _normalize_text(brand) in ["too yumm", "tooyumm"]:
        return dict(SAFETY_RULES_REGISTRY["too_yumm"])

    return dict(DEFAULT_NO_RULE)
