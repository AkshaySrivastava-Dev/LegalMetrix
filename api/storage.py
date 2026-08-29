"""
Persistent & In-Memory Repository for LegalMetrix Inspection State & History.

Provides thread-safe SQLite persistence and memory caching for inspections,
manual review logs, same-product queries, and offline batch synchronization.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger("legal_metrology.storage")


def get_db_path() -> Path:
    """Resolves the SQLite database file path."""
    project_dir = Path(__file__).resolve().parent.parent
    configured_path = os.getenv("DATABASE_PATH", "data/inspections.db")
    db_path = project_dir / configured_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


class InspectionStore:
    def __init__(self):
        self._inspections: Dict[str, Dict[str, Any]] = {}
        self._reviews: Dict[str, List[Dict[str, Any]]] = {}
        self._init_sqlite()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(get_db_path()), timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        """Initializes the SQLite schema and indexes."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS inspections (
                        inspection_id TEXT PRIMARY KEY,
                        product_name TEXT,
                        brand TEXT,
                        category TEXT,
                        variant TEXT,
                        mrp TEXT,
                        net_quantity TEXT,
                        manufacturer TEXT,
                        confidence REAL DEFAULT 0.0,
                        compliance_status TEXT DEFAULT 'UNKNOWN',
                        violations TEXT DEFAULT '[]',
                        checks TEXT DEFAULT '[]',
                        evidence TEXT DEFAULT '{}',
                        source TEXT DEFAULT 'image',
                        file_path TEXT,
                        created_at TEXT NOT NULL,
                        sync_status TEXT DEFAULT 'synced',
                        extracted_data TEXT DEFAULT '{}',
                        evaluation_result TEXT DEFAULT '{}'
                    );
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_created_at ON inspections(created_at DESC);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_product ON inspections(brand, product_name);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_sync_status ON inspections(sync_status);")
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not initialize SQLite database: {e}")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Converts a SQLite row into a dict with deserialized JSON."""
        d = dict(row)
        for json_field in ("violations", "checks", "evidence", "extracted_data", "evaluation_result"):
            val = d.get(json_field)
            if isinstance(val, str):
                try:
                    d[json_field] = json.loads(val)
                except Exception:
                    d[json_field] = [] if json_field in ("violations", "checks") else {}
            elif val is None:
                d[json_field] = [] if json_field in ("violations", "checks") else {}
        return d

    def save_inspection(
        self,
        category: Optional[str] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
        evaluation_result: Optional[Dict[str, Any]] = None,
        confidence_data: Optional[Dict[str, Any]] = None,
        evidence_data: Optional[Dict[str, Any]] = None,
        inspection_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        insp_id = inspection_id or kwargs.get("inspection_id") or f"INSP-{uuid.uuid4().hex[:8].upper()}"
        extracted = dict(extracted_data or kwargs.get("extracted", {}))
        eval_res = dict(evaluation_result or kwargs.get("evaluation", {}))
        created_at = kwargs.get("created_at") or datetime.now(timezone.utc).isoformat()

        # Extract normalized flat fields
        product_name = kwargs.get("product_name") or extracted.get("product_name")
        brand = kwargs.get("brand") or extracted.get("brand")
        variant = kwargs.get("variant") or extracted.get("variant")
        mrp = kwargs.get("mrp") or extracted.get("mrp")
        net_quantity = kwargs.get("net_quantity") or extracted.get("net_quantity")
        manufacturer = kwargs.get("manufacturer") or extracted.get("manufacturer")
        confidence = float(kwargs.get("confidence", 0.0) or eval_res.get("confidence", 0.0))
        compliance_status = (
            kwargs.get("compliance_status")
            or eval_res.get("overall_status")
            or eval_res.get("compliance_status")
            or "UNKNOWN"
        )
        violations = kwargs.get("violations") or eval_res.get("findings") or []
        checks = kwargs.get("checks") or eval_res.get("findings") or []
        evidence = evidence_data or kwargs.get("evidence") or {}
        source = kwargs.get("source", "image")
        file_path = kwargs.get("file_path")
        sync_status = kwargs.get("sync_status", "synced")

        if product_name and "product_name" not in extracted:
            extracted["product_name"] = product_name
        if brand and "brand" not in extracted:
            extracted["brand"] = brand
        if variant and "variant" not in extracted:
            extracted["variant"] = variant
        if mrp and "mrp" not in extracted:
            extracted["mrp"] = mrp
        if net_quantity and "net_quantity" not in extracted:
            extracted["net_quantity"] = net_quantity
        if manufacturer and "manufacturer" not in extracted:
            extracted["manufacturer"] = manufacturer

        # In-Memory Cache Record
        record = {
            "inspection_id": insp_id,
            "product_name": product_name,
            "brand": brand,
            "category": category or kwargs.get("category"),
            "variant": variant,
            "mrp": str(mrp) if mrp is not None else None,
            "net_quantity": str(net_quantity) if net_quantity is not None else None,
            "manufacturer": str(manufacturer) if manufacturer is not None else None,
            "confidence": confidence,
            "compliance_status": compliance_status,
            "violations": violations,
            "checks": checks,
            "evidence": evidence,
            "source": source,
            "file_path": file_path,
            "sync_status": sync_status,
            "extracted_data": extracted,
            "confidence_data": confidence_data or kwargs.get("confidence", {}),
            "evidence_data": evidence,
            "evaluation_result": eval_res,
            "created_at": created_at,
        }
        self._inspections[insp_id] = record

        # SQLite Persistence
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO inspections (
                        inspection_id, product_name, brand, category, variant,
                        mrp, net_quantity, manufacturer, confidence, compliance_status,
                        violations, checks, evidence, source, file_path,
                        created_at, sync_status, extracted_data, evaluation_result
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        insp_id,
                        product_name,
                        brand,
                        category or kwargs.get("category"),
                        variant,
                        str(mrp) if mrp is not None else None,
                        str(net_quantity) if net_quantity is not None else None,
                        str(manufacturer) if manufacturer is not None else None,
                        confidence,
                        compliance_status,
                        json.dumps(violations),
                        json.dumps(checks),
                        json.dumps(evidence),
                        source,
                        file_path,
                        created_at,
                        sync_status,
                        json.dumps(extracted),
                        json.dumps(eval_res),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not persist inspection to SQLite: {e}")

        return insp_id

    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        # Check in-memory first
        if inspection_id in self._inspections:
            mem_rec = self._inspections[inspection_id]
            extracted = mem_rec.get("extracted_data", {})
            eval_res = mem_rec.get("evaluation_result", {})
            return {
                "inspection_id": inspection_id,
                "product_name": mem_rec.get("product_name") or extracted.get("product_name"),
                "brand": mem_rec.get("brand") or extracted.get("brand"),
                "category": mem_rec.get("category"),
                "variant": mem_rec.get("variant") or extracted.get("variant"),
                "mrp": str(mem_rec.get("mrp") or extracted.get("mrp")) if (mem_rec.get("mrp") or extracted.get("mrp")) is not None else None,
                "net_quantity": str(mem_rec.get("net_quantity") or extracted.get("net_quantity")) if (mem_rec.get("net_quantity") or extracted.get("net_quantity")) is not None else None,
                "manufacturer": str(mem_rec.get("manufacturer") or extracted.get("manufacturer")) if (mem_rec.get("manufacturer") or extracted.get("manufacturer")) is not None else None,
                "confidence": float(mem_rec.get("confidence") or eval_res.get("confidence", 0.0) or 0.0),
                "compliance_status": mem_rec.get("compliance_status") or eval_res.get("overall_status") or eval_res.get("compliance_status") or "UNKNOWN",
                "violations": mem_rec.get("violations") or eval_res.get("findings") or [],
                "checks": mem_rec.get("checks") or eval_res.get("findings") or [],
                "evidence": mem_rec.get("evidence") or mem_rec.get("evidence_data") or {},
                "source": mem_rec.get("source", "image"),
                "file_path": mem_rec.get("file_path"),
                "created_at": mem_rec.get("created_at"),
                "sync_status": mem_rec.get("sync_status", "synced"),
                "extracted_data": extracted,
                "evaluation_result": eval_res,
            }

        # Check SQLite
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inspections WHERE inspection_id = ?", (inspection_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            logger.warning(f"Error reading from SQLite: {e}")
        return None

    def list_all_inspections(self) -> List[Dict[str, Any]]:
        """Returns all inspections in memory (fallback to SQLite if empty)."""
        if self._inspections:
            return list(self._inspections.values())
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inspections ORDER BY created_at DESC")
                rows = cursor.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception:
            return []

    def get_inspections(
        self,
        limit: int = 50,
        offset: int = 0,
        compliance_status: Optional[str] = None,
        sync_status: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieves paginated inspections from SQLite with metadata count."""
        query = "SELECT * FROM inspections"
        count_query = "SELECT COUNT(*) FROM inspections"
        conditions = []
        params: List[Any] = []

        if compliance_status:
            conditions.append("UPPER(compliance_status) = ?")
            params.append(compliance_status.upper())
        if sync_status:
            conditions.append("LOWER(sync_status) = ?")
            params.append(sync_status.lower())

        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            query += where_clause
            count_query += where_clause

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]

                cursor.execute(query, params + [limit, offset])
                rows = cursor.fetchall()
                items = [self._row_to_dict(r) for r in rows]
                return items, total
        except Exception as e:
            logger.warning(f"SQLite pagination failed: {e}")
            all_items = self.list_all_inspections()
            return all_items[offset : offset + limit], len(all_items)

    def get_same_product(
        self,
        brand: Optional[str] = None,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        variant: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Queries SQLite for past inspections matching brand, product_name, category, or variant."""
        conditions = []
        params: List[Any] = []

        if brand:
            conditions.append("LOWER(brand) LIKE ?")
            params.append(f"%{brand.strip().lower()}%")
        if product_name:
            conditions.append("LOWER(product_name) LIKE ?")
            params.append(f"%{product_name.strip().lower()}%")
        if category:
            conditions.append("LOWER(category) = ?")
            params.append(category.strip().lower())
        if variant:
            conditions.append("LOWER(variant) LIKE ?")
            params.append(f"%{variant.strip().lower()}%")

        if not conditions:
            return []

        query = f"SELECT * FROM inspections WHERE {' OR '.join(conditions)} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"SQLite same product query failed: {e}")
            return []

    def record_manual_review(self, inspection_id: str, review_record: Dict[str, Any]) -> None:
        if inspection_id not in self._reviews:
            self._reviews[inspection_id] = []
        self._reviews[inspection_id].append(review_record)

    def get_manual_reviews(self, inspection_id: str) -> List[Dict[str, Any]]:
        return self._reviews.get(inspection_id, [])

    def process_sync_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch synchronizes offline inspection records idempotently.
        Handles duplicates by updating existing records, isolates failures per item.
        """
        synced_count = 0
        failed_count = 0
        results = []

        for item in records:
            try:
                insp_id = item.get("inspection_id")
                if not insp_id:
                    insp_id = f"INSP-{uuid.uuid4().hex[:8].upper()}"
                    item["inspection_id"] = insp_id

                existing = self.get_inspection(insp_id)
                item["sync_status"] = "synced"
                self.save_inspection(**item)

                action = "updated" if existing else "created"
                results.append({
                    "inspection_id": insp_id,
                    "status": "synced",
                    "action": action,
                    "reason": "Successfully synchronized" if not existing else "Existing record updated",
                })
                synced_count += 1
            except Exception as e:
                failed_count += 1
                results.append({
                    "inspection_id": item.get("inspection_id", "unknown"),
                    "status": "failed",
                    "action": "none",
                    "reason": str(e),
                })

        return {
            "total_received": len(records),
            "synced_count": synced_count,
            "failed_count": failed_count,
            "results": results,
        }

    def clear(self) -> None:
        self._inspections.clear()
        self._reviews.clear()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM inspections")
                conn.commit()
        except Exception:
            pass


# Global singleton instance for the app lifecycle
db = InspectionStore()
