"""
Unit and Integration Tests for Image-based Inspection API (POST /api/inspection/scan).
"""

import io
from unittest.mock import MagicMock, patch
import cv2
from fastapi.testclient import TestClient
import numpy as np
import pytest

from main import app

client = TestClient(app)


def _create_test_image_bytes(width: int = 100, height: int = 100) -> bytes:
    """Creates a dummy valid PNG image in-memory."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)
    # Put some dummy text lines
    cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


class TestImageInspectionAPI:

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_compliant(self, mock_get_pipeline):
        """
        Tests successful image scan resulting in COMPLIANT status with high OCR confidence.
        """
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": True,
            "quality": {"status": "GOOD", "issues": []},
            "category": "food",
            "fields": {
                "product_name": {"value": "Demo Biscuit", "confidence": 0.95, "box": [[10, 10], [100, 10], [100, 30], [10, 30]]},
                "brand": {"value": "DemoBrand", "confidence": 0.96, "box": [[10, 40], [100, 40], [100, 60], [10, 60]]},
                "mrp": {"value": "50", "confidence": 0.98, "box": [[10, 70], [100, 70], [100, 90], [10, 90]]},
                "net_quantity": {"value": "200 g", "confidence": 0.94, "box": [[10, 100], [100, 100], [100, 120], [10, 120]]},
                "manufacturer": {"value": "ABC Foods Ltd, Mumbai", "confidence": 0.92, "box": [[10, 130], [200, 130], [200, 150], [10, 150]]},
                "country_of_origin": {"value": "India", "confidence": 0.97, "box": [[10, 160], [100, 160], [100, 180], [10, 180]]},
                "manufacturing_date": {"value": "08/2026", "confidence": 0.91, "box": [[10, 190], [100, 190], [100, 210], [10, 210]]},
                "consumer_care": {"value": "care@demo.com", "confidence": 0.93, "box": [[10, 220], [100, 220], [100, 240], [10, 240]]},
            },
            "raw_ocr": [
                {"text": "Demo Biscuit", "confidence": 0.95},
                {"text": "MRP Rs. 50", "confidence": 0.98},
            ],
            "evidence": {},
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("test_package.png", io.BytesIO(image_bytes), "image/png")}
        data = {"category": "food", "inspection_id": "INSP-IMG-001"}

        response = client.post("/api/inspection/scan", files=files, data=data)
        assert response.status_code == 200
        res = response.json()

        assert res["inspection_id"] == "INSP-IMG-001"
        assert res["category"] == "food"
        assert res["overall_status"] == "COMPLIANT"
        assert res["passed_count"] == 7
        assert res["failed_count"] == 0
        assert res["uncertain_count"] == 0
        assert len(res["manual_reviews"]) == 0
        assert res["image_quality"]["status"] == "GOOD"
        assert res["raw_ocr_count"] == 2

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_auto_detect_category(self, mock_get_pipeline):
        """
        Tests category auto-detection when category is omitted from the form data.
        """
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": True,
            "quality": {"status": "GOOD", "issues": []},
            "category": "beverage",
            "fields": {
                "product_name": {"value": "Fresh Apple Juice", "confidence": 0.95, "box": []},
                "mrp": {"value": "40", "confidence": 0.95, "box": []},
                "net_quantity": {"value": "200 ml", "confidence": 0.95, "box": []},
                "manufacturer": {"value": "Juice Co Ltd", "confidence": 0.95, "box": []},
                "country_of_origin": {"value": "India", "confidence": 0.95, "box": []},
                "manufacturing_date": {"value": "08/2026", "confidence": 0.95, "box": []},
                "consumer_care": {"value": "care@juice.com", "confidence": 0.95, "box": []},
            },
            "raw_ocr": [{"text": "Fresh Apple Juice", "confidence": 0.95}],
            "evidence": {},
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("juice_box.png", io.BytesIO(image_bytes), "image/png")}

        response = client.post("/api/inspection/scan", files=files)
        assert response.status_code == 200
        res = response.json()
        assert res["category"] == "beverage"
        assert res["overall_status"] == "COMPLIANT"

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_low_confidence_routes_to_needs_review(self, mock_get_pipeline):
        """
        Tests that low confidence OCR extractions correctly route to NEEDS_REVIEW
        without inventing a non-compliance violation.
        """
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": True,
            "quality": {"status": "ACCEPTABLE", "issues": ["Minor glare"]},
            "category": "food",
            "fields": {
                "product_name": {"value": "Demo Biscuit", "confidence": 0.95, "box": []},
                "mrp": {"value": "50", "confidence": 0.95, "box": []},
                "net_quantity": {"value": "200 g", "confidence": 0.95, "box": []},
                "manufacturer": {"value": "ABC Foods", "confidence": 0.43, "box": [[10, 10], [50, 50]]},
                "country_of_origin": {"value": "India", "confidence": 0.95, "box": []},
                "manufacturing_date": {"value": "08/2026", "confidence": 0.95, "box": []},
                "consumer_care": {"value": "care@demo.com", "confidence": 0.95, "box": []},
            },
            "raw_ocr": [],
            "evidence": {},
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("blurry_mfg.png", io.BytesIO(image_bytes), "image/png")}
        data = {"category": "food"}

        response = client.post("/api/inspection/scan", files=files, data=data)
        assert response.status_code == 200
        res = response.json()
        assert res["overall_status"] == "NEEDS_REVIEW"
        assert res["uncertain_count"] == 1
        assert len(res["manual_reviews"]) == 1
        assert res["manual_reviews"][0]["field"] == "manufacturer"
        assert res["manual_reviews"][0]["confidence"] == 43.0
        assert res["manual_reviews"][0]["requires_manual_review"] is True

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_non_compliant_missing_fields(self, mock_get_pipeline):
        """
        Tests that missing mandatory fields are evaluated as NON_COMPLIANT.
        """
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": True,
            "quality": {"status": "GOOD", "issues": []},
            "category": "food",
            "fields": {
                "product_name": {"value": "Demo Biscuit", "confidence": 0.95, "box": []},
                "mrp": None,  # Missing mandatory MRP
                "net_quantity": {"value": "200 g", "confidence": 0.95, "box": []},
                "manufacturer": {"value": "ABC Foods", "confidence": 0.95, "box": []},
                "country_of_origin": None,  # Missing mandatory origin
                "manufacturing_date": {"value": "08/2026", "confidence": 0.95, "box": []},
                "consumer_care": {"value": "care@demo.com", "confidence": 0.95, "box": []},
            },
            "raw_ocr": [],
            "evidence": {},
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("missing_fields.png", io.BytesIO(image_bytes), "image/png")}
        data = {"category": "food"}

        response = client.post("/api/inspection/scan", files=files, data=data)
        assert response.status_code == 200
        res = response.json()
        assert res["overall_status"] == "NON_COMPLIANT"
        assert res["failed_count"] == 2

    def test_scan_image_empty_file_fails(self):
        """Tests that uploading an empty file returns HTTP 400."""
        files = {"image": ("empty.png", io.BytesIO(b""), "image/png")}
        response = client.post("/api/inspection/scan", files=files)
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_scan_image_corrupt_file_fails(self):
        """Tests that uploading corrupted non-image bytes returns HTTP 400."""
        files = {"image": ("corrupt.png", io.BytesIO(b"not a valid image content"), "image/png")}
        response = client.post("/api/inspection/scan", files=files)
        assert response.status_code == 400
        assert "decode" in response.json()["detail"].lower()

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_bad_quality_fails(self, mock_get_pipeline):
        """Tests that bad image quality from AI quality checker returns HTTP 400 with diagnostic issues."""
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": False,
            "quality": {
                "status": "BAD",
                "issues": ["Image too blurry (Laplacian variance 12.4 < 50.0)"],
            },
            "category": "unknown",
            "fields": {},
            "raw_ocr": [],
            "message": "Image quality insufficient for reliable OCR",
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("blurry.png", io.BytesIO(image_bytes), "image/png")}

        response = client.post("/api/inspection/scan", files=files)
        assert response.status_code == 400
        assert "quality check failed" in response.json()["detail"].lower()

    @patch("api.routes.get_ai_pipeline")
    def test_scan_image_unknown_category_fails(self, mock_get_pipeline):
        """Tests that when category cannot be auto-detected and is not provided, HTTP 400 is returned."""
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_pipeline.inspect_image.return_value = {
            "success": True,
            "quality": {"status": "GOOD", "issues": []},
            "category": "unknown",
            "fields": {"mrp": {"value": "50", "confidence": 0.95}},
            "raw_ocr": [],
            "evidence": {},
        }

        image_bytes = _create_test_image_bytes()
        files = {"image": ("unknown.png", io.BytesIO(image_bytes), "image/png")}

        response = client.post("/api/inspection/scan", files=files)
        assert response.status_code == 400
        assert "category could not be determined" in response.json()["detail"].lower()

    def test_scan_image_invalid_category_fails(self):
        """Tests that an unsupported category specified in form data returns HTTP 404."""
        with patch("api.routes.get_ai_pipeline") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_get_pipeline.return_value = mock_pipeline
            mock_pipeline.inspect_image.return_value = {
                "success": True,
                "quality": {"status": "GOOD", "issues": []},
                "category": "non_existent_category",
                "fields": {},
                "raw_ocr": [],
                "evidence": {},
            }

            image_bytes = _create_test_image_bytes()
            files = {"image": ("test.png", io.BytesIO(image_bytes), "image/png")}
            data = {"category": "non_existent_category"}

            response = client.post("/api/inspection/scan", files=files, data=data)
            assert response.status_code == 404
