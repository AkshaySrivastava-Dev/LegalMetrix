"""
Tests for Offline Sync and SQLite Persistence Engine (Member 5).
Validates POST /api/sync endpoint, duplicate handling, and SQLite persistence.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from backend.services.database_service import init_db, get_inspection, process_sync_batch, get_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM inspections;")
        conn.commit()
    yield
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM inspections;")
        conn.commit()



def test_sync_offline_records_success():
    payload = {
        "records": [
            {
                "inspection_id": "INSP-TEST-SYNC-001",
                "product_name": "Britannia Good Day Cookies",
                "brand": "Britannia",
                "category": "packaged_food",
                "variant": "Butter 100g",
                "mrp": "30.00",
                "net_quantity": "100 g",
                "manufacturer": "Britannia Industries Ltd",
                "confidence": 0.985,
                "compliance_status": "COMPLIANT",
                "violations": [],
                "checks": [{"field": "mrp", "passed": True}],
                "evidence": {"is_360_scan": False},
                "source": "mobile_offline",
                "created_at": "2026-08-30T04:15:00.000Z",
                "sync_status": "pending"
            }
        ]
    }

    response = client.post("/api/sync", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert data["total_received"] == 1
    assert data["synced_count"] == 1
    assert data["failed_count"] == 0
    assert len(data["results"]) == 1
    assert data["results"][0]["inspection_id"] == "INSP-TEST-SYNC-001"
    assert data["results"][0]["status"] == "synced"

    # Verify SQLite persistence
    persisted = get_inspection("INSP-TEST-SYNC-001")
    assert persisted is not None
    assert persisted["inspection_id"] == "INSP-TEST-SYNC-001"
    assert persisted["product_name"] == "Britannia Good Day Cookies"
    assert persisted["sync_status"] == "synced"


def test_sync_duplicate_idempotency():
    payload = {
        "records": [
            {
                "inspection_id": "INSP-TEST-SYNC-DUP-001",
                "product_name": "Parle-G Glucose Biscuits",
                "brand": "Parle",
                "category": "packaged_food",
                "mrp": "10.00",
                "net_quantity": "130 g",
                "compliance_status": "COMPLIANT",
                "confidence": 0.96,
                "source": "mobile_offline",
            }
        ]
    }

    # First sync -> created
    resp1 = client.post("/api/sync", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["results"][0]["action"] == "created"

    # Second sync -> updated (idempotent, no duplicates)
    resp2 = client.post("/api/sync", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["results"][0]["action"] == "updated"
    assert resp2.json()["synced_count"] == 1

    # Verify SQLite still has only 1 row
    persisted = get_inspection("INSP-TEST-SYNC-DUP-001")
    assert persisted is not None
    assert persisted["inspection_id"] == "INSP-TEST-SYNC-DUP-001"


def test_sync_batch_multiple_records():
    payload = {
        "records": [
            {
                "inspection_id": "INSP-BATCH-001",
                "product_name": "Tata Salt",
                "brand": "Tata",
                "category": "packaged_food",
                "mrp": "28.00",
                "net_quantity": "1 kg",
                "compliance_status": "COMPLIANT",
            },
            {
                "inspection_id": "INSP-BATCH-002",
                "product_name": "Fortune Sunflower Oil",
                "brand": "Fortune",
                "category": "edible_oil",
                "mrp": "165.00",
                "net_quantity": "1 L",
                "compliance_status": "COMPLIANT",
            }
        ]
    }

    response = client.post("/api/sync", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_received"] == 2
    assert data["synced_count"] == 2
    assert data["failed_count"] == 0
