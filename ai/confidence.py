"""
Confidence Level module.

Converts raw confidence scores to prototype levels:
- HIGH: confidence >= 0.90
- MEDIUM: 0.60 <= confidence < 0.90
- LOW: confidence < 0.60
"""

from typing import Dict, Any


def get_confidence_level(confidence: float) -> str:
    """
    Get prototype confidence level from score.
    
    Args:
        confidence: Confidence score (0.0 to 1.0)
        
    Returns:
        "HIGH", "MEDIUM", or "LOW"
    """
    if confidence >= 0.90:
        return "HIGH"
    elif confidence >= 0.60:
        return "MEDIUM"
    else:
        return "LOW"


def add_confidence_levels(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add confidence levels to all extracted fields.
    
    Args:
        fields: Dict of extracted fields
        
    Returns:
        Updated fields dict with 'level' added to each field
    """
    result = {}
    for key, value in fields.items():
        if value is not None and isinstance(value, dict):
            conf = value.get("confidence", 0.0)
            value["level"] = get_confidence_level(conf)
        result[key] = value
    return result


if __name__ == "__main__":
    # Test
    test_confidences = [0.95, 0.90, 0.85, 0.75, 0.60, 0.59, 0.50, 0.30]
    
    for conf in test_confidences:
        level = get_confidence_level(conf)
        print(f"Confidence: {conf:.2f} -> Level: {level}")
    
    # Test with fields
    test_fields = {
        "mrp": {"value": "50", "confidence": 0.97, "box": []},
        "net_quantity": {"value": "200", "confidence": 0.75, "box": [], "unit": "g"},
        "manufacturer": {"value": "ABC Ltd", "confidence": 0.55, "box": []},
        "date": None
    }
    
    result = add_confidence_levels(test_fields)
    import json
    print("\nWith levels:")
    print(json.dumps(result, indent=2))