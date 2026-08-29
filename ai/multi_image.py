"""
Multi-Image Fusion Module.

Combines inspection results from multiple views (front, back, side)
of the same product into a single consolidated result.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class FieldCandidate:
    """Represents a candidate value for a field from one source image."""
    value: Any
    confidence: float
    level: str
    source: str
    box: List[List[int]]
    unit: Optional[str] = None


class MultiImageFusion:
    """Fuses inspection results from multiple product views."""
    
    # Standard fields that can be extracted
    STANDARD_FIELDS = [
        'product_name', 'brand', 'mrp', 'net_quantity',
        'manufacturer', 'packer', 'importer',
        'country_of_origin', 'manufacturing_date', 'expiry_date', 'batch_number'
    ]
    
    def __init__(self):
        pass
    
    def fuse_results(
        self,
        results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fuse multiple single-image inspection results.
        
        Args:
            results: Dict mapping source_name ('front', 'back', 'side') 
                    to single-image inspection result
                    
        Returns:
            Fused product result
        """
        # Collect all fields from all sources
        field_candidates = {field: [] for field in self.STANDARD_FIELDS}
        all_raw_ocr = {}
        all_quality = {}
        all_evidence = {}
        all_categories = []
        
        for source_name, result in results.items():
            if not result.get('success', False):
                continue
                
            # Collect raw OCR
            if 'raw_ocr' in result:
                all_raw_ocr[source_name] = result['raw_ocr']
            
            # Collect quality
            if 'quality' in result:
                all_quality[source_name] = result['quality']
            
            # Collect evidence
            if 'evidence' in result:
                all_evidence[source_name] = result['evidence']
            
            # Collect category
            if 'category' in result and result['category'] != 'unknown':
                all_categories.append(result['category'])
            
            # Collect field candidates
            fields = result.get('fields', {})
            for field_name in self.STANDARD_FIELDS:
                field_data = fields.get(field_name)
                if field_data and field_data.get('value') is not None:
                    candidate = FieldCandidate(
                        value=field_data['value'],
                        confidence=field_data.get('confidence', 0.0),
                        level=field_data.get('level', 'LOW'),
                        source=source_name,
                        box=field_data.get('box', []),
                        unit=field_data.get('unit')
                    )
                    field_candidates[field_name].append(candidate)
        
        # Determine final category (majority vote or first non-unknown)
        final_category = self._resolve_category(all_categories)
        
        # Fuse each field
        fused_fields = {}
        for field_name in self.STANDARD_FIELDS:
            candidates = field_candidates[field_name]
            fused_fields[field_name] = self._fuse_field(field_name, candidates)
        
        # Check if all images were bad quality
        all_bad = all(q.get('status') == 'BAD' for q in all_quality.values())
        
        return {
            'success': not all_bad,
            'category': final_category,
            'fields': fused_fields,
            'quality': all_quality,
            'raw_ocr': all_raw_ocr,
            'evidence': all_evidence,
            'images': {k: k for k in results.keys()}  # placeholder for filenames
        }
    
    def _resolve_category(self, categories: List[str]) -> str:
        """Resolve final category from multiple candidates."""
        if not categories:
            return 'unknown'
        
        # Count occurrences
        from collections import Counter
        counts = Counter(categories)
        
        # Return most common
        return counts.most_common(1)[0][0]
    
    def _fuse_field(
        self,
        field_name: str,
        candidates: List[FieldCandidate]
    ) -> Dict[str, Any]:
        """
        Fuse field candidates from multiple images.
        
        Logic:
        - No candidates -> null
        - One candidate -> use it
        - Multiple candidates with SAME value -> use that value, combine sources
        - Multiple candidates with DIFFERENT values -> CONFLICT resolution
        """
        if not candidates:
            return None
        
        # Group by value (normalize for comparison)
        value_groups: Dict[str, List[FieldCandidate]] = {}
        for c in candidates:
            key = self._normalize_value_for_comparison(field_name, c.value)
            if key not in value_groups:
                value_groups[key] = []
            value_groups[key].append(c)
        
        if len(value_groups) == 1:
            # Single unique value across all sources
            value = next(iter(value_groups.keys()))
            group = value_groups[value]
            return self._build_field_result(value, group, 'FOUND')
        
        # Multiple different values - attempt conflict resolution
        return self._resolve_conflict(field_name, value_groups)
    
    def _normalize_value_for_comparison(self, field_name: str, value: Any) -> str:
        """Normalize value for comparison across sources."""
        if value is None:
            return ""
        s = str(value).strip()
        # For MRP, normalize currency format
        if field_name == 'mrp':
            s = re.sub(r'[₹\s]', '', s)
        # For dates, normalize separators
        if field_name in ['manufacturing_date', 'expiry_date']:
            s = s.replace('-', '/')
        # Case-insensitive for text fields
        if field_name in ['product_name', 'brand', 'manufacturer', 'packer', 'importer', 'country_of_origin', 'batch_number']:
            s = s.upper()
        return s
    
    def _resolve_conflict(
        self,
        field_name: str,
        value_groups: Dict[str, List[FieldCandidate]]
    ) -> Dict[str, Any]:
        """
        Resolve conflicts between different values from different images.
        
        Strategy:
        1. Prefer value with highest confidence
        2. If confidence similar, prefer value from more reliable source (back for regulatory info, front for branding)
        3. If still ambiguous, mark as CONFLICT
        """
        candidates_list = []
        for value, group in value_groups.items():
            for c in group:
                candidates_list.append({
                    'value': value,
                    'source': c.source,
                    'confidence': c.confidence,
                    'level': c.level,
                    'box': c.box
                })
        
        # Try to pick the best candidate based on confidence and source priority
        best_candidate = None
        best_score = -1
        
        # Source priority depends on field type
        source_priority = self._get_source_priority(field_name)
        
        for value, group in value_groups.items():
            # Use highest confidence in group
            group_best = max(group, key=lambda c: c.confidence)
            # Calculate composite score
            confidence_score = group_best.confidence
            source_score = source_priority.get(group_best.source, 0)
            composite = confidence_score * 10 + source_score
            
            if composite > best_score:
                best_score = composite
                best_candidate = group_best
        
        # If we have a clear winner (significantly better), use it with MEDIUM confidence
        if best_candidate and best_score > 0:
            # Check if there's a close competitor
            second_best_score = -1
            for value, group in value_groups.items():
                group_best = max(group, key=lambda c: c.confidence)
                confidence_score = group_best.confidence
                source_score = source_priority.get(group_best.source, 0)
                composite = confidence_score * 10 + source_score
                if composite != best_score and composite > second_best_score:
                    second_best_score = composite
            
            # If winner is clearly better (score diff > 5), use it
            if best_score - second_best_score > 5:
                return self._build_field_result(
                    best_candidate.value,
                    [best_candidate],
                    'FOUND'
                )
        
        # Otherwise, return conflict
        return {
            'value': None,
            'confidence': None,
            'level': None,
            'status': 'CONFLICT',
            'candidates': candidates_list
        }
    
    def _get_source_priority(self, field_name: str) -> Dict[str, int]:
        """Get source priority for conflict resolution based on field type."""
        # Back/side typically have regulatory info, front has branding
        priorities = {
            'mrp': {'front': 3, 'back': 2, 'side': 1},
            'net_quantity': {'back': 3, 'side': 2, 'front': 1},
            'manufacturer': {'back': 3, 'side': 2, 'front': 1},
            'packer': {'back': 3, 'side': 2, 'front': 1},
            'importer': {'back': 3, 'side': 2, 'front': 1},
            'country_of_origin': {'back': 3, 'side': 2, 'front': 1},
            'manufacturing_date': {'back': 3, 'side': 2, 'front': 1},
            'expiry_date': {'back': 3, 'side': 2, 'front': 1},
            'batch_number': {'back': 3, 'side': 2, 'front': 1},
            'product_name': {'front': 3, 'back': 1, 'side': 1},
            'brand': {'front': 3, 'back': 1, 'side': 1},
        }
        return priorities.get(field_name, {'front': 1, 'back': 1, 'side': 1})
    
    def _build_field_result(
        self,
        value: Any,
        candidates: List[FieldCandidate],
        status: str
    ) -> Dict[str, Any]:
        """Build standard field result from candidates with same value."""
        # Use highest confidence as primary
        best = max(candidates, key=lambda c: c.confidence)
        
        sources = []
        for c in candidates:
            sources.append({
                'image': c.source,
                'box': c.box,
                'confidence': c.confidence,
                'level': c.level
            })
        
        result = {
            'value': value,
            'confidence': round(best.confidence, 4),
            'level': best.level,
            'status': status,
            'sources': sources
        }
        
        # Add unit if present in any candidate (for net_quantity)
        for c in candidates:
            if c.unit:
                result['unit'] = c.unit
                break
        
        return result
    
    def _build_conflict_result(
        self,
        field_name: str,
        value_groups: Dict[str, List[FieldCandidate]]
    ) -> Dict[str, Any]:
        """Build conflict result when values differ across images."""
        candidates_list = []
        for value, group in value_groups.items():
            for c in group:
                candidates_list.append({
                    'value': value,
                    'source': c.source,
                    'confidence': c.confidence,
                    'level': c.level,
                    'box': c.box
                })
        
        return {
            'value': None,
            'confidence': None,
            'level': None,
            'status': 'CONFLICT',
            'candidates': candidates_list
        }


def create_fusion() -> MultiImageFusion:
    """Factory function to create multi-image fusion."""
    return MultiImageFusion()


if __name__ == "__main__":
    # Simple test
    fusion = create_fusion()
    
    # Test case 1: Same value from multiple images
    test_results = {
        'front': {
            'success': True,
            'category': 'food',
            'quality': {'status': 'GOOD', 'reasons': [], 'metrics': {}},
            'fields': {
                'mrp': {'value': '50', 'confidence': 0.92, 'level': 'HIGH', 'box': [[10,10],[50,10],[50,30],[10,30]]},
                'product_name': {'value': 'ABC Biscuits', 'confidence': 0.94, 'level': 'HIGH', 'box': [[10,50],[150,50],[150,70],[10,70]]},
                'brand': {'value': 'ABC', 'confidence': 0.90, 'level': 'HIGH', 'box': [[10,30],[80,30],[80,50],[10,50]]},
            },
            'raw_ocr': [{'text': 'MRP 50', 'confidence': 0.92, 'box': [[10,10],[50,10],[50,30],[10,30]]}],
            'evidence': {}
        },
        'back': {
            'success': True,
            'category': 'food',
            'quality': {'status': 'GOOD', 'reasons': [], 'metrics': {}},
            'fields': {
                'mrp': {'value': '50', 'confidence': 0.97, 'level': 'HIGH', 'box': [[20,20],[60,20],[60,40],[20,40]]},
                'manufacturer': {'value': 'ABC Foods Ltd', 'confidence': 0.91, 'level': 'HIGH', 'box': [[20,60],[200,60],[200,80],[20,80]]},
                'manufacturing_date': {'value': '27/11/25', 'confidence': 0.93, 'level': 'HIGH', 'box': [[20,100],[120,100],[120,120],[20,120]]},
                'expiry_date': {'value': '27/11/26', 'confidence': 0.93, 'level': 'HIGH', 'box': [[20,140],[120,140],[120,160],[20,160]]},
            },
            'raw_ocr': [{'text': 'MRP 50', 'confidence': 0.97, 'box': [[20,20],[60,20],[60,40],[20,40]]}],
            'evidence': {}
        },
        'side': {
            'success': True,
            'category': 'food',
            'quality': {'status': 'GOOD', 'reasons': [], 'metrics': {}},
            'fields': {
                'net_quantity': {'value': '200', 'confidence': 0.96, 'level': 'HIGH', 'unit': 'g', 'box': [[30,30],[100,30],[100,50],[30,50]]},
                'batch_number': {'value': 'B12345', 'confidence': 0.92, 'level': 'HIGH', 'box': [[30,70],[120,70],[120,90],[30,90]]},
            },
            'raw_ocr': [{'text': 'Net Qty 200g', 'confidence': 0.96, 'box': [[30,30],[100,30],[100,50],[30,50]]}],
            'evidence': {}
        }
    }
    
    result = fusion.fuse_results(test_results)
    import json
    print("Test 1 - Normal fusion:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*50)
    
    # Test case 2: Conflict with clear winner
    conflict_results = {
        'front': {
            'success': True,
            'category': 'food',
            'quality': {'status': 'GOOD', 'reasons': [], 'metrics': {}},
            'fields': {
                'mrp': {'value': '10', 'confidence': 0.95, 'level': 'HIGH', 'box': [[10,10],[50,10],[50,30],[10,30]]}
            },
            'raw_ocr': [],
            'evidence': {}
        },
        'back': {
            'success': True,
            'category': 'food',
            'quality': {'status': 'GOOD', 'reasons': [], 'metrics': {}},
            'fields': {
                'mrp': {'value': '20', 'confidence': 0.61, 'level': 'MEDIUM', 'box': [[20,20],[60,20],[60,40],[20,40]]}
            },
            'raw_ocr': [],
            'evidence': {}
        }
    }
    
    result2 = fusion.fuse_results(conflict_results)
    print("Test 2 - Conflict with clear winner:")
    print(json.dumps(result2, indent=2))