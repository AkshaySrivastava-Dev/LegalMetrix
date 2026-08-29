"""
Integration Tests for Member 2 Backend Endpoints in LegalMetrix.
Tests Real Scan (Photo/Video), Compliance, Persistence, Offline Sync, and Comparison.
"""

import io
import cv2
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
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
        assert data["mock_ai"] is False
        assert data["mock_compliance"] is False

    def test_scan_image_validation_errors(self):
        # 1. Empty file
        files = {"image": ("empty.png", b"", "image/png")}
        resp = client.post("/api/scan", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

        # 2. Corrupted / un-decodable file
        files = {"image": ("corrupted.png", b"not-a-real-image", "image/png")}
        resp = client.post("/api/scan", files=files)
        assert resp.status_code == 400
        assert "decode" in resp.json()["detail"].lower()

        # 3. Missing image file
        resp = client.post("/api/scan")
        assert resp.status_code == 422

    def test_ocr_failure_does_not_produce_hardcoded_data(self):
        """Proves that OCR pipeline failure raises an error and does NOT silently fabricate mock data."""
        with patch("api.routes.get_ai_pipeline") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.inspect_image.side_effect = RuntimeError("OCR Engine Failure")
            mock_get_pipeline.return_value = mock_pipeline

            # Create real valid 100x100 PNG bytes
            img = np.zeros((100, 100, 3), dtype=np.uint8)
            _, encoded = cv2.imencode(".png", img)
            files = {"image": ("test_package.png", encoded.tobytes(), "image/png")}
            resp = client.post("/api/scan", files=files)

            assert resp.status_code == 500
            assert "OCR processing failed" in resp.json()["detail"]

    def test_bad_image_quality_rejected_without_compliance(self):
        """Proves that bad image quality returns HTTP 400 and halts before rule evaluation."""
        with patch("api.routes.get_ai_pipeline") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_pipeline.inspect_image.return_value = {
                "quality": {"status": "BAD", "issues": ["Image is too blurry", "Glare detected"]},
                "fields": {},
                "category": "food",
            }
            mock_get_pipeline.return_value = mock_pipeline

            img = np.zeros((100, 100, 3), dtype=np.uint8)
            _, encoded = cv2.imencode(".png", img)
            files = {"image": ("blurry_package.png", encoded.tobytes(), "image/png")}
            resp = client.post("/api/scan", files=files)

            assert resp.status_code == 400
            assert "Image quality check failed" in resp.json()["detail"]
            assert "blurry" in resp.json()["detail"]

    def test_compliance_engine_error_does_not_return_compliant(self):
        """Proves that invalid category / compliance engine failure raises 404/400 and NEVER converts to COMPLIANT."""
        payload = {
            "category": "invalid_nonexistent_category_xyz",
            "extracted_data": {"product_name": "Test Product"},
        }
        resp = client.post("/api/compliance", json=payload)
        assert resp.status_code == 404
        assert "No rule definition found" in resp.json()["detail"]

    def test_direct_compliance_endpoint(self):
        payload = {
            "category": "food",
            "extracted_data": {
                "product_name": "Nutri Crunch Wheat Bread",
                "brand": "Healthy Bakers",
                "mrp": "₹40.00",
                "net_quantity": "400 g",
                "manufacturer": "Healthy Bakers Pvt Ltd, Plot 45, New Delhi 110020",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@healthybakers.com",
            },
            "confidence": {
                "product_name": 95.0,
                "brand": 92.0,
                "mrp": 96.0,
                "net_quantity": 94.0,
                "manufacturer": 91.0,
                "country_of_origin": 95.0,
                "date_of_manufacture": 90.0,
                "consumer_care": 90.0,
            }
        }
        resp = client.post("/api/compliance", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "COMPLIANT"
        assert len(data["findings"]) > 0

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
            "physical_data": {
                "product_name": "Demo Biscuits",
                "mrp": "₹50",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India"
            },
            "online_data": {
                "product_name": "Demo Biscuits",
                "mrp": "₹60",
                "net_quantity": "500 g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India"
            }
        }
        resp = client.post("/api/comparison", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"] == "MISMATCH"
        assert data["fields"]["mrp"]["result"] == "MISMATCH"
        assert data["fields"]["net_quantity"]["result"] == "MATCH"
