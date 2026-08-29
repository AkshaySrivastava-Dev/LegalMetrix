"""
Database Service Adapter.
Provides isolated, thread-safe SQLite operations for inspections and offline sync.
Keeps raw SQL and storage logic decoupled from API route handlers.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("legal_metrology.database_service")


def get_db_path() -> Path:
    """Resolves the SQLite database file path."""
    backend_dir = Path(__file__).resolve().parent.parent
    configured_path = os.getenv("DATABASE_PATH", "data/inspections.db")
    db_path = backend_dir / configured_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(get_db_path()), timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the inspections table and indexes if they do not exist."""
    db_path = get_db_path()
    logger.info(f"Initializing SQLite database at: {db_path}")

    with get_connection() as conn:
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
                sync_status TEXT DEFAULT 'synced'
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_created_at ON inspections(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_product ON inspections(brand, product_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insp_sync_status ON inspections(sync_status);")
        conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Helper to convert a SQLite Row to a Python dict with deserialized JSON fields."""
    d = dict(row)
    for json_field in ("violations", "checks", "evidence"):
        val = d.get(json_field)
        if isinstance(val, str):
            try:
                d[json_field] = json.loads(val)
            except Exception:
                d[json_field] = [] if json_field != "evidence" else {}
        elif val is None:
            d[json_field] = [] if json_field != "evidence" else {}
    return d


def save_inspection(inspection_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves an inspection record into SQLite.
    Returns the saved inspection record as a dictionary.
    """
    record_id = inspection_data.get("inspection_id")
    if not record_id:
        import uuid
        record_id = f"insp_{uuid.uuid4().hex[:12]}"

    created_at = inspection_data.get("created_at") or datetime.utcnow().isoformat() + "Z"
    violations_json = json.dumps(inspection_data.get("violations", []))
    checks_json = json.dumps(inspection_data.get("checks", []))
    evidence_json = json.dumps(inspection_data.get("evidence", {}))

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO inspections (
                inspection_id, product_name, brand, category, variant,
                mrp, net_quantity, manufacturer, confidence, compliance_status,
                violations, checks, evidence, source, file_path,
                created_at, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                inspection_data.get("product_name"),
                inspection_data.get("brand"),
                inspection_data.get("category"),
                inspection_data.get("variant"),
                inspection_data.get("mrp"),
                inspection_data.get("net_quantity"),
                inspection_data.get("manufacturer"),
                float(inspection_data.get("confidence", 0.0)),
                inspection_data.get("compliance_status", "UNKNOWN"),
                violations_json,
                checks_json,
                evidence_json,
                inspection_data.get("source", "image"),
                inspection_data.get("file_path"),
                created_at,
                inspection_data.get("sync_status", "synced"),
            ),
        )
        conn.commit()

    return get_inspection(record_id)


def get_inspection(inspection_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single inspection by its unique inspection_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inspections WHERE inspection_id = ?", (inspection_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def get_inspections(
    limit: int = 50,
    offset: int = 0,
    compliance_status: Optional[str] = None,
    sync_status: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated inspection records and total count."""
    query = "SELECT * FROM inspections"
    count_query = "SELECT COUNT(*) FROM inspections"
    conditions = []
    params: List[Any] = []

    if compliance_status:
        conditions.append("compliance_status = ?")
        params.append(compliance_status.upper())

    if sync_status:
        conditions.append("sync_status = ?")
        params.append(sync_status.lower())

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        query += where_clause
        count_query += where_clause

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"

    with get_connection() as conn:
        cursor = conn.cursor()
        # Count total
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Fetch records
        query_params = list(params) + [limit, offset]
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        items = [_row_to_dict(r) for r in rows]

    return items, total


def get_same_product(
    brand: Optional[str] = None,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
    variant: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Finds past inspections matching any provided product attributes (brand, product_name, category, variant).
    """
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

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [_row_to_dict(r) for r in rows]


def mark_synced(inspection_id: str, status: str = "synced") -> bool:
    """Updates sync status for a record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inspections SET sync_status = ? WHERE inspection_id = ?",
            (status, inspection_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def process_sync_batch(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Processes a batch of offline inspection records.
    Handles duplicates, validation, and inserts/updates safely.
    """
    synced_count = 0
    failed_count = 0
    results = []

    for item in records:
        try:
            insp_id = item.get("inspection_id")
            if not insp_id:
                import uuid
                insp_id = f"insp_{uuid.uuid4().hex[:12]}"
                item["inspection_id"] = insp_id

            # Check if record already exists
            existing = get_inspection(insp_id)
            item["sync_status"] = "synced"

            save_inspection(item)

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
