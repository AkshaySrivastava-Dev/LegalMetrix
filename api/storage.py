"""
In-Memory Repository for LegalMetrix Inspection State & History.

Provides thread-safe persistence for inspections and manual review logs
during the hackathon demo lifecycle.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


class InspectionStore:
    def __init__(self):
        self._inspections: Dict[str, Dict[str, Any]] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}

    def save_inspection(
        self,
        category: str,
        extracted_data: Dict[str, Any],
        evaluation_result: Dict[str, Any],
        confidence_data: Optional[Dict[str, Any]] = None,
        evidence_data: Optional[Dict[str, Any]] = None,
        inspection_id: Optional[str] = None,
    ) -> str:
        insp_id = inspection_id or f"INSP-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "inspection_id": insp_id,
            "category": category,
            "extracted_data": extracted_data,
            "confidence_data": confidence_data or {},
            "evidence_data": evidence_data or {},
            "evaluation_result": evaluation_result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._inspections[insp_id] = record
        return insp_id

    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        return self._inspections.get(inspection_id)

    def list_all_inspections(self) -> List[Dict[str, Any]]:
        return list(self._inspections.values())

    def record_manual_review(self, inspection_id: str, review_record: Dict[str, Any]) -> None:
        if inspection_id not in self._reviews:
            self._reviews[inspection_id] = []
        self._reviews[inspection_id].append(review_record)

    def get_manual_reviews(self, inspection_id: str) -> List[Dict[str, Any]]:
        return self._reviews.get(inspection_id, [])

    def clear(self) -> None:
        self._inspections.clear()
        self._reviews.clear()


# Global singleton instance for the app lifecycle
db = InspectionStore()
