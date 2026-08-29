"""
Integration Tests for Member 2 Backend Endpoints in LegalMetrix.
Tests Scan (Photo/Video), Compliance, Persistence, Offline Sync, and Comparison.
"""

import io
import pytest
from fastapi.testclient import TestClient
from main import app
from api.storage import db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db.clear()
    yield
    db.clear()


class TestBackendIntegration:
    def test_api_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "LegalMetrix" in data["service"]
        assert data["database_status"] == "connected"

    def test_scan_image_success(self):
        # Create dummy PNG image bytes
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"image": ("test_package.png", image_content, "image/png")}
        resp = client.post("/api/scan", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "inspection_id" in data
        assert data["product_name"] is not None
        assert data["compliance_status"] in ("COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW")
        assert data["source"] == "image"

    def test_scan_image_validation_errors(self):
        # Empty file
        files = {"image": ("empty.png", b"", "image/png")}
        resp = client.post("/api/scan", files=files)
        assert resp.status_code == 400
        assert resp.json()["error"] is True

        # Invalid file format
        files = {"image": ("notes.txt", b"plain text content", "text/plain")}
        resp = client.post("/api/scan", files=files)
        assert resp.status_code == 400
        assert resp.json()["error"] is True

    def test_scan_360_video_success(self):
        video_content = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"
        files = {"video": ("scan_rotation.mp4", video_content, "video/mp4")}
        resp = client.post("/api/scan/360", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "inspection_id" in data
        assert data["source"] == "video_360"
        assert "evidence" in data

    def test_direct_compliance_endpoint(self):
        payload = {
            "product_name": "Nutri Crunch Wheat Bread",
            "brand": "Healthy Bakers",
            "mrp": "₹40.00 (incl. of all taxes)",
            "net_quantity": "400 g",
            "manufacturer": "Healthy Bakers Pvt Ltd, Plot 45, New Delhi 110020",
        }
        resp = client.post("/api/compliance", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["compliance_status"] in ("COMPLIANT", "NON_COMPLIANT")
        assert len(data["checks"]) > 0

    def test_get_inspection_by_id_and_not_found(self):
        # Save an inspection first
        saved_id = db.save_inspection(
            product_name="Test Product",
            brand="Test Brand",
            mrp="₹100",
            net_quantity="1 kg",
            compliance_status="COMPLIANT",
        )
        resp = client.get(f"/api/inspection/{saved_id}")
        assert resp.status_code == 200
        assert resp.json()["inspection_id"] == saved_id
        assert resp.json()["product_name"] == "Test Product"

        # Not found
        resp_404 = client.get("/api/inspection/non_existent_id_9999")
        assert resp_404.status_code == 404

    def test_list_inspections_pagination(self):
        for i in range(5):
            db.save_inspection(
                product_name=f"Product {i}",
                brand="Test Brand",
                compliance_status="COMPLIANT",
            )
        resp = client.get("/api/inspections?limit=3&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_same_product_history_query(self):
        db.save_inspection(
            product_name="CleanMaster Floor Cleaner",
            brand="CleanMaster",
            category="household",
            mrp="₹120",
        )
        db.save_inspection(
            product_name="CleanMaster Dishwash Gel",
            brand="CleanMaster",
            category="household",
            mrp="₹55",
        )
        resp = client.get("/api/inspections/same-product?brand=CleanMaster")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

    def test_offline_sync_batch_and_alias(self):
        payload = {
            "records": [
                {
                    "inspection_id": "OFFLINE-001",
                    "product_name": "Organic Almonds",
                    "brand": "Natures Best",
                    "mrp": "₹250.00",
                    "net_quantity": "200 g",
                    "compliance_status": "COMPLIANT",
                    "source": "offline_sync",
                },
                {
                    "inspection_id": "OFFLINE-002",
                    "product_name": "Pure Honey",
                    "brand": "Natures Best",
                    "mrp": "₹180.00",
                    "net_quantity": "250 g",
                    "compliance_status": "COMPLIANT",
                    "source": "offline_sync",
                },
            ]
        }
        # Primary sync endpoint
        resp = client.post("/api/sync", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_received"] == 2
        assert data["synced_count"] == 2
        assert data["failed_count"] == 0

        # Duplicate sync (idempotency check)
        resp_dup = client.post("/api/sync", json=payload)
        assert resp_dup.status_code == 200
        dup_data = resp_dup.json()
        assert dup_data["synced_count"] == 2
        assert dup_data["results"][0]["action"] == "updated"

        # Client alias endpoint: POST /api/inspections/sync
        resp_alias = client.post("/api/inspections/sync", json=payload)
        assert resp_alias.status_code == 200
        assert resp_alias.json()["synced_count"] == 2

    def test_comparison_endpoint(self):
        payload = {
            "brand": "Dhara Agro",
            "product_name": "Pure Gold Refined Mustard Oil",
            "mrp": "₹190.00",
            "net_quantity": "1 L / 910 g",
        }
        resp = client.post("/api/comparison", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "mismatched"
        assert "mrp" in data["mismatched_fields"]
        assert len(data["matched_fields"]) > 0
