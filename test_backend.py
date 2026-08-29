"""
Automated Test Suite for Legal Metrology Inspection Backend.
Validates all required API endpoints, error handling, mock flows, sync, and comparison features.
"""

import sys
import io
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.database_service import init_db
from backend.services.ai_service import is_mock_ai_enabled
from backend.services.compliance_service import is_mock_compliance_enabled

client = TestClient(app)
__test__ = False


def test_01_health_check():
    print("\n[TEST 1] Checking Health Endpoint: GET /api/health ...")
    response = client.get("/api/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Legal Metrology Backend"
    assert data["database_status"] == "connected"
    assert "timestamp" in data
    assert "uploads_dir" in data
    print(" -> PASSED: Health endpoint is OK.")


def test_02_scan_image_success():
    print("\n[TEST 2] Checking Photo Scan: POST /api/scan ...")
    dummy_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
    files = {"image": ("test_package.png", dummy_image, "image/png")}

    response = client.post("/api/scan", files=files)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert "inspection_id" in data
    assert data["product_name"] is not None
    assert data["mrp"] is not None
    assert data["net_quantity"] is not None
    assert data["compliance_status"] in ("COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT")
    assert isinstance(data["checks"], list)
    assert isinstance(data["violations"], list)
    print(f" -> PASSED: Inspection created successfully (ID: {data['inspection_id']}, Status: {data['compliance_status']})")
    return data["inspection_id"], data["product_name"], data["brand"]


def test_03_scan_image_validation_errors():
    print("\n[TEST 3] Checking Image Scan Validation Errors ...")
    # Empty file
    empty_file = io.BytesIO(b"")
    files = {"image": ("empty.png", empty_file, "image/png")}
    response = client.post("/api/scan", files=files)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    print(" -> PASSED: Empty image upload correctly rejected with 400.")

    # Unsupported format
    txt_file = io.BytesIO(b"Hello world")
    files = {"image": ("notes.txt", txt_file, "text/plain")}
    response = client.post("/api/scan", files=files)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    print(" -> PASSED: Unsupported file extension correctly rejected with 400.")


def test_04_direct_compliance_endpoint():
    print("\n[TEST 4] Checking Direct Compliance: POST /api/compliance ...")
    payload = {
        "product_name": "Nutri Crunch Wheat Bread",
        "brand": "Healthy Bakers",
        "category": "packaged_food",
        "mrp": "₹40.00 (incl. of all taxes)",
        "net_quantity": "400 g",
        "manufacturer": "Healthy Bakers Pvt Ltd, Plot 45, Okhla Phase III, New Delhi 110020",
    }
    response = client.post("/api/compliance", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["compliance_status"] == "COMPLIANT"
    assert len(data["violations"]) == 0
    print(" -> PASSED: Direct compliance evaluation returned COMPLIANT.")

    # Test non-compliant payload (missing MRP and Net Qty)
    bad_payload = {
        "product_name": "Unknown Powder",
        "brand": "NoName",
    }
    response_bad = client.post("/api/compliance", json=bad_payload)
    assert response_bad.status_code == 200
    data_bad = response_bad.json()
    assert data_bad["compliance_status"] == "NON_COMPLIANT"
    assert len(data_bad["violations"]) > 0
    print(" -> PASSED: Incomplete payload correctly identified as NON_COMPLIANT with violations.")


def test_05_get_inspection_by_id(inspection_id: str):
    print(f"\n[TEST 5] Checking GET /api/inspection/{inspection_id} ...")
    response = client.get(f"/api/inspection/{inspection_id}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["inspection_id"] == inspection_id
    print(f" -> PASSED: Fetched inspection details for ID: {inspection_id}")

    # Test not found
    resp_404 = client.get("/api/inspection/non_existent_id_999")
    assert resp_404.status_code == 404
    print(" -> PASSED: Non-existent ID returned 404 NotFound.")


def test_06_get_inspections_history():
    print("\n[TEST 6] Checking GET /api/inspections history list ...")
    response = client.get("/api/inspections?limit=10&offset=0")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    print(f" -> PASSED: Retrieved {len(data['items'])} items (total: {data['total']}).")


def test_07_get_same_product(brand: str, product_name: str):
    print(f"\n[TEST 7] Checking GET /api/inspections/same-product for brand '{brand}' ...")
    response = client.get(f"/api/inspections/same-product?brand={brand}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    print(f" -> PASSED: Found {len(items)} matching past inspections.")


def test_08_offline_sync():
    print("\n[TEST 8] Checking POST /api/sync batch offline synchronization ...")
    sync_payload = {
        "records": [
            {
                "inspection_id": "offline_insp_001",
                "product_name": "Organic Almonds",
                "brand": "Natures Best",
                "category": "dry_fruits",
                "mrp": "₹250.00",
                "net_quantity": "200 g",
                "manufacturer": "Natures Best Organics, Mumbai 400001",
                "compliance_status": "COMPLIANT",
                "confidence": 0.92,
                "source": "mobile_offline",
            },
            {
                "inspection_id": "offline_insp_002",
                "product_name": "Mineral Water",
                "brand": "AquaPure",
                "category": "beverages",
                "mrp": "₹20.00",
                "net_quantity": "1 L",
                "manufacturer": "AquaPure Beverages Ltd, Pune 411001",
                "compliance_status": "COMPLIANT",
                "confidence": 0.95,
                "source": "mobile_offline",
            },
        ]
    }
    response = client.post("/api/sync", json=sync_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["total_received"] == 2
    assert data["synced_count"] == 2
    assert data["failed_count"] == 0
    print(f" -> PASSED: Batch sync processed {data['synced_count']} records.")

    # Test idempotent duplicate sync
    response_dup = client.post("/api/sync", json=sync_payload)
    assert response_dup.status_code == 200
    data_dup = response_dup.json()
    assert data_dup["synced_count"] == 2
    assert data_dup["results"][0]["action"] == "updated"
    print(" -> PASSED: Duplicate sync handled safely and idempotently.")


def test_09_scan_360_video():
    print("\n[TEST 9] Checking 360 Video Scan: POST /api/scan/360 ...")
    dummy_video = io.BytesIO(b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41")
    files = {"video": ("scan_rotation.mp4", dummy_video, "video/mp4")}

    response = client.post("/api/scan/360", files=files)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["source"] == "video_360"
    assert data["inspection_id"] is not None
    assert "evidence" in data
    print(f" -> PASSED: 360 Video scan recorded (ID: {data['inspection_id']}, Source: {data['source']})")


def test_10_comparison(saved_inspection_id: str):
    print("\n[TEST 10] Checking Physical vs Online Comparison: POST /api/comparison ...")
    # 1. Direct matched comparison
    match_payload = {
        "brand": "Britannica Foods",
        "product_name": "Krunchy Treat Butter Cookies",
        "mrp": "₹45.00",
        "net_quantity": "150 g",
    }
    response = client.post("/api/comparison", json=match_payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] in ("matched", "mismatched")
    print(f" -> PASSED: Comparison returned status: '{data['status']}' with {len(data['matched_fields'])} matched fields.")

    # 2. Mismatched MRP comparison
    mismatch_payload = {
        "brand": "Dhara Agro",
        "product_name": "Pure Gold Refined Mustard Oil",
        "mrp": "₹190.00",  # Higher than online catalogue standard (160)
        "net_quantity": "1 L / 910 g",
    }
    resp_mismatch = client.post("/api/comparison", json=mismatch_payload)
    assert resp_mismatch.status_code == 200
    data_mismatch = resp_mismatch.json()
    assert data_mismatch["status"] == "mismatched"
    assert "mrp" in data_mismatch["mismatched_fields"]
    print(" -> PASSED: Price discrepancy (mrp) successfully detected between packaging and online benchmark.")

    # 3. Comparison using saved inspection ID
    resp_by_id = client.post("/api/comparison", json={"inspection_id": saved_inspection_id})
    assert resp_by_id.status_code == 200
    print(f" -> PASSED: Comparison by saved inspection_id '{saved_inspection_id}' executed successfully.")

    # 4. Unavailable comparison
    unavail_payload = {
        "brand": "RandomUnlistedBrand999",
        "product_name": "Unlisted Product",
    }
    resp_unavail = client.post("/api/comparison", json=unavail_payload)
    assert resp_unavail.status_code == 200
    data_unavail = resp_unavail.json()
    assert data_unavail["status"] == "unavailable"
    print(" -> PASSED: Unlisted product returned 'unavailable' gracefully.")


def test_11_mock_mode_configuration():
    print("\n[TEST 11] Checking Mock Mode Configuration Helpers ...")
    assert is_mock_ai_enabled() is True
    assert is_mock_compliance_enabled() is True
    print(" -> PASSED: Mock mode helpers respond correctly.")


def run_all_tests():
    print("==================================================")
    print("STARTING FULL END-TO-END BACKEND INTEGRATION TESTS")
    print("==================================================")
    init_db()

    test_01_health_check()
    insp_id, prod_name, brand = test_02_scan_image_success()
    test_03_scan_image_validation_errors()
    test_04_direct_compliance_endpoint()
    test_05_get_inspection_by_id(insp_id)
    test_06_get_inspections_history()
    test_07_get_same_product(brand, prod_name)
    test_08_offline_sync()
    test_09_scan_360_video()
    test_10_comparison(insp_id)
    test_11_mock_mode_configuration()

    print("\n==================================================")
    print("ALL 11 TEST SUITES PASSED PERFECTLY!")
    print("==================================================")


if __name__ == "__main__":
    run_all_tests()
