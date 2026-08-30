"""
Safety Watchlist and Ingredient Analysis Module for LegalMetrix.

Analyzes extracted ingredients against statutory watchlists, regulatory declaration
schedules (FSSAI / Legal Metrology), allergen disclosures, and food additive limits.

CRITICAL POLICY:
- Never claims that a component is inherently harmful or that the product is unsafe.
- Designates matching items objectively as "Safety Review Required" with clear statutory rationale.
"""

import re
from typing import Dict, Any, List, Optional, Tuple


# Configurable Statutory Safety Watchlist
DEFAULT_SAFETY_WATCHLIST = [
    {
        "id": "WL-FLV-001",
        "name": "Monosodium Glutamate (MSG)",
        "code": "INS 621 / E621",
        "category": "Flavor Enhancer",
        "patterns": [r"\b(?:monosodium\s+glutamate|msg|ins\s*621|e\s*621|glutamate|ajinomoto)\b"],
        "reason": "Statutory advisory disclosure required under FSSR (Packaging & Labelling). Mandatory notice: Not recommended for infants below 12 months.",
        "statutory_ref": "FSSAI Reg. 2.2.1 / Legal Metrology Schedule"
    },
    {
        "id": "WL-SWT-001",
        "name": "Aspartame (Artificial Sweetener)",
        "code": "INS 951 / E951",
        "category": "Artificial Sweetener",
        "patterns": [r"\b(?:aspartame|ins\s*951|e\s*951)\b"],
        "reason": "Statutory warning mandatory on principal display panel: 'Contains Artificial Sweetener & Phenylalanine. Not recommended for children or phenylketonurics.'",
        "statutory_ref": "FSSAI (Food Product Standards & Food Additives) Reg. 3.1.3"
    },
    {
        "id": "WL-SWT-002",
        "name": "Sucralose / Non-Caloric Sweetener",
        "code": "INS 955 / E955",
        "category": "Artificial Sweetener",
        "patterns": [r"\b(?:sucralose|ins\s*955|e\s*955|acesulfame\s*k|ins\s*950|e\s*950|saccharin|ins\s*954)\b"],
        "reason": "Non-caloric sweetener requires statutory quantitative declaration in mg/kg and 'Not recommended for children' advisory.",
        "statutory_ref": "FSSAI Labelling Reg. 2020 / Rule 6"
    },
    {
        "id": "WL-PRS-001",
        "name": "Sodium Benzoate / Class II Preservative",
        "code": "INS 211 / E211",
        "category": "Preservative",
        "patterns": [r"\b(?:sodium\s+benzoate|ins\s*211|e\s*211|class\s*ii\s*preservative|preservative\s*\(?211\)?)\b"],
        "reason": "Class II preservative subject to statutory Maximum Permissible Limits (MPL) in PPM under Food Safety Regulations.",
        "statutory_ref": "FSSAI Food Additives Schedule 1"
    },
    {
        "id": "WL-PRS-002",
        "name": "Potassium Sorbate / Sulphites",
        "code": "INS 202 / E202",
        "category": "Preservative",
        "patterns": [r"\b(?:potassium\s+sorbate|ins\s*202|e\s*202|sodium\s+metabisulphite|ins\s*223|e\s*223|sulphite|sulfite)\b"],
        "reason": "Chemical preservative requiring statutory category declaration and permissible ppm threshold monitoring.",
        "statutory_ref": "FSSAI Food Additives Schedule 1"
    },
    {
        "id": "WL-COL-001",
        "name": "Permitted Synthetic Food Colour (Tartrazine / Sunset Yellow)",
        "code": "INS 102 / INS 110",
        "category": "Synthetic Colour",
        "patterns": [r"\b(?:tartrazine|ins\s*102|e\s*102|sunset\s+yellow|ins\s*110|e\s*110|allura\s+red|ins\s*129|e\s*129|brilliant\s+blue|ins\s*133|synthetic\s+food\s+colou?r|synthetic\s+colou?r)\b"],
        "reason": "Mandatory statutory declaration required on display label: 'CONTAINS PERMITTED SYNTHETIC FOOD COLOUR(S)'.",
        "statutory_ref": "Legal Metrology Rules 2011 & FSSAI 2.4.5"
    },
    {
        "id": "WL-FAT-001",
        "name": "Palm Oil / Hydrogenated Vegetable Fat",
        "code": "FAT-SURV-01",
        "category": "Fats & Oils",
        "patterns": [r"\b(?:palm\s+oil|palmolein|hydrogenated\s+vegetable\s+oil|vanaspati|trans\s+fat|interesterified\s+vegetable\s+fat)\b"],
        "reason": "Statutory nutritional declaration of saturated fat and trans-fat percentage per 100g/serving required under FSSAI Labelling Regulations.",
        "statutory_ref": "FSSAI Mandatory Nutritional Labelling Amendment"
    },
    {
        "id": "WL-ALG-001",
        "name": "Major Food Allergen (Gluten / Wheat / Nuts / Soy / Milk)",
        "code": "ALLERGEN-FSSAI",
        "category": "Allergen Advisory",
        "patterns": [r"\b(?:gluten|wheat\s+flour|maida|peanut|groundnut|tree\s+nuts?|almonds?|cashews?|soya?|soy\s+lecithin|milk\s+solids?|lactose|casein|crustacean|fish|egg)\b"],
        "reason": "Mandatory allergen declaration required under FSSAI Labelling Regulations (in bold or separate 'Contains' statement).",
        "statutory_ref": "FSSAI (Labelling and Display) Regulations 2020"
    }
]


def extract_ingredients_from_ocr(ocr_results: List[Dict[str, Any]]) -> Tuple[Optional[str], List[str]]:
    """
    Extracts ingredients block and structured list from OCR text lines.

    Returns:
        (raw_text, list_of_individual_ingredients)
    """
    if not ocr_results:
        return None, []

    full_text = " ".join([item.get('text', '').strip() for item in ocr_results if item.get('text')])
    
    # 1. Regex search for Ingredients section
    ingredients_marker = re.search(
        r'(?:INGREDIENTS|INGREDIENT|INGREDIENTS\s*\/|INGRÉDIENTS|CONTENTS|COMPOSITION)\s*[:\-]\s*(.+?)(?=(?:NUTRITION|NUTRITIONAL|MFG|MFD|EXP|BEST\s+BEFORE|STORE\s+IN|M\.R\.P|MRP|NET\s+QTY|NET\s+WT|BATCH|LIC|FSSAI|MANUFACTURED|CUSTOMER\s+CARE|$))',
        full_text,
        re.IGNORECASE | re.DOTALL
    )

    extracted_text = None
    if ingredients_marker:
        extracted_text = ingredients_marker.group(1).strip()
    else:
        # Fallback: find line containing 'INGREDIENTS'
        for i, item in enumerate(ocr_results):
            t = item.get('text', '').strip()
            if re.search(r'^(?:INGREDIENTS|CONTENTS|COMPOSITION)\b', t, re.IGNORECASE):
                # Aggregate following 1-3 lines
                lines = [t]
                for next_item in ocr_results[i+1:i+4]:
                    next_t = next_item.get('text', '').strip()
                    if re.search(r'^(?:NUTRITION|MFG|EXP|MRP|NET|BATCH|FSSAI|LIC)\b', next_t, re.IGNORECASE):
                        break
                    lines.append(next_t)
                extracted_text = " ".join(lines)
                extracted_text = re.sub(r'^(?:INGREDIENTS|CONTENTS|COMPOSITION)\s*[:\-]?\s*', '', extracted_text, flags=re.IGNORECASE).strip()
                break

    if not extracted_text:
        return None, []

    # Clean up trailing punctuation / noise
    extracted_text = re.sub(r'[\.\;\s]+$', '', extracted_text).strip()

    # Split into structured ingredients
    raw_tokens = re.split(r'[,;•\n\r]+', extracted_text)
    ingredients_list = []
    for token in raw_tokens:
        clean = token.strip()
        clean = re.sub(r'^[\-\*/•\d\.\)]+\s*', '', clean).strip()
        if clean and len(clean) > 1 and not re.match(r'^(?:and|or|contains|may\s+contain)$', clean, re.IGNORECASE):
            ingredients_list.append(clean)

    return extracted_text, ingredients_list


def analyze_safety_watchlist(
    ingredients_text: Optional[str] = None,
    ingredients_list: Optional[List[str]] = None,
    watchlist: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Evaluates ingredients against the statutory safety watchlist.

    Returns:
        Structured safety analysis object.
    """
    active_watchlist = watchlist or DEFAULT_SAFETY_WATCHLIST
    
    parts = []
    if isinstance(ingredients_text, str):
        parts.append(ingredients_text)
    elif isinstance(ingredients_text, (list, tuple)):
        parts.extend([str(x) for x in ingredients_text])
        
    if isinstance(ingredients_list, str):
        parts.append(ingredients_list)
    elif isinstance(ingredients_list, (list, tuple)):
        parts.extend([str(x) for x in ingredients_list])
        
    text_to_search = " ".join(parts)
    
    flagged_components = []
    seen_ids = set()

    if text_to_search.strip():
        for entry in active_watchlist:
            if entry["id"] in seen_ids:
                continue
            for pat in entry.get("patterns", []):
                match = re.search(pat, text_to_search, re.IGNORECASE)
                if match:
                    seen_ids.add(entry["id"])
                    flagged_components.append({
                        "id": entry["id"],
                        "name": entry["name"],
                        "code": entry["code"],
                        "category": entry["category"],
                        "detected_token": match.group(0),
                        "reason": entry["reason"],
                        "statutory_reference": entry.get("statutory_ref", "FSSAI / Legal Metrology Regulations")
                    })
                    break

    review_required = len(flagged_components) > 0
    
    if review_required:
        summary = f"Safety Review Required: {len(flagged_components)} statutory advisory component(s) detected for regulatory verification."
        status_label = "SAFETY_REVIEW_REQUIRED"
    else:
        summary = "Ingredients declaration analyzed. No statutory watchlist advisories flagged."
        status_label = "COMPLIANT_DECLARATION"

    return {
        "status": status_label,
        "review_required": review_required,
        "summary": summary,
        "flagged_count": len(flagged_components),
        "flagged_components": flagged_components,
        "extracted_ingredients": ingredients_list or [],
        "raw_ingredients_text": ingredients_text or ""
    }
