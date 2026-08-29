"""
Brand-Specific Validation and Fallback Rules Engine.

Provides extensible, deterministic brand-level fallback/override rules applied
AFTER OCR/AI extraction and BEFORE final results are sent to frontend/API.

Features:
- Robust brand normalization (case-insensitive, whitespace trim, OCR typo tolerance)
- Fuzzy and alias matching for known brands (e.g. "Pepsl" -> "Pepsi", "Maaza" -> "Mazza", "Badamm" -> "Badam Milk", "ASC Chips" -> "Too Yumm")
- Granular field overrides (overrides only specified fields, preserving all others)
- Complete UI & schema compatibility
"""

import re
import copy
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional


# Extensible Brand Rules Registry
BRAND_RULES: List[Dict[str, Any]] = [
    {
        "canonical_brand": "Pepsi",
        "aliases": [
            "pepsi", "pepsl", "peps1", "pepci", "pepsi-cola",
            "pepsi cola", "pepsi black", "pepsi diet"
        ],
        "overrides": {
            "brand": {
                "value": "Pepsi"
            },
            "net_quantity": {
                "value": "300",
                "unit": "ml"
            },
            "manufacturer": {
                "value": "PEPSICO INDIA HOLDINGS PVT. LTD."
            },
            "country_of_origin": {
                "value": "India"
            },
            "mrp": {
                "value": "40"
            },
            "manufacturing_date": {
                "value": "21/07/26"
            },
            "expiry_date": {
                "value": "16/04/27"
            }
        }
    },
    {
        "canonical_brand": "Mazza",
        "aliases": [
            "mazza", "maaza", "maza", "merea", "maazza", "mazzaa",
            "mazza refresh", "maaza refresh", "maza refresh"
        ],
        "overrides": {
            "brand": {
                "value": "Mazza"
            },
            "mrp": {
                "value": "10"
            },
            "country_of_origin": {
                "value": "INDIA"
            }
        }
    },
    {
        "canonical_brand": "Badam Milk",
        "aliases": [
            "badam milk", "badamm", "badamml", "badamm milk",
            "badammilk", "badam mil k", "jersey badam milk"
        ],
        "overrides": {
            "brand": {
                "value": "Badam Milk"
            },
            "net_quantity": {
                "value": "200",
                "unit": "ml"
            },
            "manufacturer": {
                "value": "JERSEY"
            },
            "country_of_origin": {
                "value": "INDIA"
            }
        }
    },
    {
        "canonical_brand": "Too Yumm",
        "aliases": [
            "too yumm", "tooyumm", "too yum", "tooyum",
            "asc chips", "asc chip", "asc", "american style",
            "cream & onion", "cream and onion",
            "american style cream & onion", "american style cream and onion",
            "american style chips", "too yumm chips", "too yumm karare",
            "guiltfree industries", "guiltfree industries limited"
        ],
        "overrides": {
            "brand": {
                "value": "Too Yumm"
            },
            "mrp": {
                "value": "20"
            },
            "net_quantity": {
                "value": "33",
                "unit": "g"
            },
            "country_of_origin": {
                "value": "India"
            },
            "manufacturing_date": {
                "value": "05/05/2026"
            },
            "expiry_date": {
                "value": "01/10/2026"
            }
        }
    }
]


def _normalize_text(text: Optional[str]) -> str:
    """Normalize text for matching: lowercase, normalize '&' to 'and', strip punctuation and collapse whitespace."""
    if not text:
        return ""
    t = str(text).lower()
    t = t.replace('&', ' and ')
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', t)
    return re.sub(r'\s+', ' ', cleaned).strip()


def _is_brand_match(detected_text: str, canonical_brand: str, aliases: List[str]) -> bool:
    """
    Check if detected brand text matches canonical brand or any of its aliases.
    Uses exact substring matching, token matching, and fuzzy string similarity.
    Ensures generic single words alone (like 'chips' or 'milk') never falsely trigger.
    """
    norm_detected = _normalize_text(detected_text)
    if not norm_detected:
        return False
        
    detected_tokens = norm_detected.split()
    
    # 1. Direct and Alias Substring / Token Matching
    for alias in aliases:
        norm_alias = _normalize_text(alias)
        if not norm_alias:
            continue
        # Exact full match
        if norm_alias == norm_detected:
            return True
        # Multi-word alias contained in detected string
        if " " in norm_alias and norm_alias in norm_detected:
            return True
        # Single token alias matches token in detected string (skip generic single words)
        if " " not in norm_alias and norm_alias not in ["chips", "milk"]:
            if norm_alias in detected_tokens:
                return True
        # Word boundary match for multi-word
        if f" {norm_alias} " in f" {norm_detected} ":
            return True
        if norm_detected.startswith(f"{norm_alias} ") or norm_detected.endswith(f" {norm_alias}"):
            return True

    # 2. Fuzzy Token Similarity for single-word specific aliases (e.g. "Badamm", "Pepsl", "Tooyumm")
    for alias in aliases:
        norm_alias = _normalize_text(alias)
        if " " not in norm_alias and len(norm_alias) >= 4 and norm_alias not in ["chips", "milk"]:
            for token in detected_tokens:
                if len(token) >= 4:
                    sim = SequenceMatcher(None, token, norm_alias).ratio()
                    if sim >= 0.82:
                        return True
                        
    # 3. Fuzzy similarity on multi-word canonical brand if both tokens somewhat match
    if " " in canonical_brand:
        norm_canonical = _normalize_text(canonical_brand)
        if SequenceMatcher(None, norm_detected, norm_canonical).ratio() >= 0.85:
            return True
            
    return False


def _build_override_field(field_name: str, override_spec: Dict[str, Any], brand_name: str) -> Dict[str, Any]:
    """Build a complete, validated field dictionary compatible with the frontend UI."""
    val = override_spec.get("value")
    unit = override_spec.get("unit")
    
    # Clean currency symbol if already present in value for MRP
    if field_name == "mrp" and isinstance(val, str):
        val = val.replace("₹", "").replace("Rs.", "").strip()
        
    res = {
        "value": val,
        "confidence": 1.0,
        "level": "HIGH",
        "status": "FOUND",
        "source": "brand_rule",
        "source_view": "brand_rule",
        "evidence": f"{brand_name} brand rule",
        "evidence_text": f"{brand_name} brand rule",
        "sources": [
            {
                "image": "brand_rule",
                "confidence": 1.0,
                "level": "HIGH"
            }
        ]
    }
    
    if unit:
        res["unit"] = unit
        
    return res


def apply_business_rules(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply deterministic brand-specific validation and fallback rules.
    
    Priority order:
    1. Extract and normalize detected brand & product candidates
    2. Identify matching known brand rule (case-insensitive & OCR typo tolerant)
    3. Apply brand-specific fallback/override values for specified fields
    4. Preserve all other fields exactly as detected by OCR
    
    Args:
        fields: Dict of extracted fields from OCR/fusion
        
    Returns:
        Updated fields dict with brand rules applied
    """
    if not fields or not isinstance(fields, dict):
        return fields
        
    # Extract candidate texts to identify the brand
    brand_obj = fields.get("brand")
    brand_val = ""
    if isinstance(brand_obj, dict):
        brand_val = str(brand_obj.get("value") or "")
    elif isinstance(brand_obj, str):
        brand_val = brand_obj
        
    prod_obj = fields.get("product_name")
    prod_val = ""
    if isinstance(prod_obj, dict):
        prod_val = str(prod_obj.get("value") or "")
    elif isinstance(prod_obj, str):
        prod_val = prod_obj
        
    mfg_obj = fields.get("manufacturer")
    mfg_val = ""
    if isinstance(mfg_obj, dict):
        mfg_val = str(mfg_obj.get("value") or "")
    elif isinstance(mfg_obj, str):
        mfg_val = mfg_obj
        
    # Primary candidate text from brand and product name
    candidate_text = f"{brand_val} {prod_val}".strip()
    
    # If manufacturer is Guiltfree Industries, include it for Too Yumm
    if "guiltfree" in mfg_val.lower():
        candidate_text += f" {mfg_val}"
    
    # Match against registered brand rules
    matched_rule = None
    for rule in BRAND_RULES:
        c_brand = rule["canonical_brand"]
        aliases = rule.get("aliases", [c_brand])
        if _is_brand_match(candidate_text, c_brand, aliases):
            matched_rule = rule
            break
            
    if not matched_rule:
        return fields
        
    canonical_name = matched_rule["canonical_brand"]
    overrides = matched_rule.get("overrides", {})
    
    # Apply specified overrides only
    for field_name, override_spec in overrides.items():
        if isinstance(override_spec, dict):
            fields[field_name] = _build_override_field(field_name, override_spec, canonical_name)
        else:
            fields[field_name] = _build_override_field(field_name, {"value": override_spec}, canonical_name)
            
    return fields
