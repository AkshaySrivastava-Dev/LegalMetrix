"""
Integration Tests for LegalMetrix FastAPI REST Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from api.storage import db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_storage():
    db.clear()
    yield
    db.clear()


class TestAPIEndpoints:
    # ------------------ Health & Root ------------------ #
    def test_health_check(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root_endpoint(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "legalmetrix" in resp.json()["message"].lower()

    # ------------------ Rules Endpoints ------------------ #
    def test_get_rules_valid_category(self):
        resp = client.get("/api/rules/food")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "food"
        assert len(data["rules"]) > 0

    def test_get_rules_invalid_category(self):
        resp = client.get("/api/rules/nonexistent_category_999")
        assert resp.status_code == 404
        assert "No rule definition found" in resp.json()["detail"]

    # ------------------ Compliance Evaluation Endpoint ------------------ #
    def test_post_compliance_evaluate_compliant(self):
        payload = {
            "category": "food",
            "inspection_id": "INSP-TEST-001",
            "extracted_data": {
                "product_name": "ABC Biscuits",
                "net_quantity": "500g",
                "mrp": "₹50",
                "manufacturer": "ABC Foods Ltd",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@abcfoods.com",
            },
            "confidence": {
                "product_name": 98.0,
                "net_quantity": 95.0,
                "mrp": 96.0,
                "manufacturer": 92.0,
                "country_of_origin": 97.0,
                "date_of_manufacture": 91.0,
                "consumer_care": 90.0,
            },
            "evidence": {
                "product_name": "frame_01",
                "mrp": "frame_02",
            }
        }

        resp = client.post("/api/compliance/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "COMPLIANT"
        assert data["inspection_id"] == "INSP-TEST-001"
        assert data["passed_count"] == 7
        assert len(data["findings"]) == 7

    def test_post_compliance_evaluate_with_extractions_list(self):
        payload = {
            "category": "food",
            "inspection_id": "INSP-OCR-LIST",
            "extractions": [
                {"field": "product_name", "value": "ABC Biscuits", "confidence": 0.98, "evidence": "frame_01"},
                {"field": "net_quantity", "value": "500g", "confidence": 0.95, "evidence": "frame_01"},
                {"field": "mrp", "value": "₹50", "confidence": 0.96, "evidence": "frame_02"},
                {"field": "manufacturer", "value": "ABC Foods Ltd", "confidence": 0.92, "evidence": "frame_03"},
                {"field": "country_of_origin", "value": "India", "confidence": 0.97, "evidence": "frame_03"},
                {"field": "date_of_manufacture", "value": "08/2026", "confidence": 0.91, "evidence": "frame_02"},
                {"field": "consumer_care", "value": "care@abcfoods.com", "confidence": 0.90, "evidence": "frame_04"},
            ]
        }

        resp = client.post("/api/compliance/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "COMPLIANT"
        assert data["passed_count"] == 7

    def test_post_compliance_evaluate_needs_review(self):
        payload = {
            "category": "food",
            "inspection_id": "INSP-TEST-002",
            "extracted_data": {
                "product_name": "ABC Biscuits",
                "net_quantity": "500g",
                "mrp": "₹50",
                "manufacturer": "ABC Foods",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@abcfoods.com",
            },
            "confidence": {
                "product_name": 98.0,
                "mrp": 96.0,
                "net_quantity": 94.0,
                "manufacturer": 43.0,  # Below 60%
                "country_of_origin": 92.0,
                "date_of_manufacture": 95.0,
                "consumer_care": 90.0,
            },
            "evidence": {
                "manufacturer": "frame_03"
            }
        }

        resp = client.post("/api/compliance/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_status"] == "NEEDS_REVIEW"
        assert len(data["manual_reviews"]) == 1
        assert data["manual_reviews"][0]["field"] == "manufacturer"
        assert data["manual_reviews"][0]["requires_manual_review"] is True

    # ------------------ Manual Review Endpoint ------------------ #
    def test_post_manual_review_correct(self):
        payload = {
            "inspection_id": "INSP-TEST-002",
            "field": "manufacturer",
            "action": "CORRECT",
            "reviewer_id": "OFFICER-101",
            "ai_value": "ABC F00ds",
            "confidence": 43.0,
            "evidence": "frame_03",
            "corrected_value": "ABC Foods Ltd, Mumbai",
            "notes": "Corrected OCR misspelling from frame 3",
        }

        resp = client.post("/api/compliance/manual-review", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        review = data["review_record"]
        assert review["action"] == "CORRECT"
        assert review["ai_value"] == "ABC F00ds"  # Original preserved
        assert review["corrected_value"] == "ABC Foods Ltd, Mumbai"
        assert review["reviewer_id"] == "OFFICER-101"

    # ------------------ Reconciliation Endpoint ------------------ #
    def test_post_reconciliation_compare(self):
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

        resp = client.post("/api/reconciliation/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall"] == "MISMATCH"
        assert data["message"] == "Potential mismatch detected — officer review recommended."
        assert data["fields"]["mrp"]["result"] == "MISMATCH"
        assert data["fields"]["net_quantity"]["result"] == "MATCH"

    # ------------------ Historical Comparison Endpoint ------------------ #
    def test_historical_inspection_history_and_comparison(self):
        # 1. Create a prior inspection
        payload1 = {
            "category": "food",
            "inspection_id": "INSP-HIST-1",
            "extracted_data": {
                "brand": "DemoBrand",
                "product_name": "Demo Product",
                "category": "food",
                "variant": "500g",
                "mrp": "₹50",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India",
                "date_of_manufacture": "01/2026",
                "consumer_care": "care@demo.com",
            },
            "confidence": {"mrp": 95.0, "product_name": 98.0}
        }
        resp1 = client.post("/api/compliance/evaluate", json=payload1)
        assert resp1.status_code == 200

        # 2. Create a subsequent inspection with MRP change
        payload2 = {
            "category": "food",
            "inspection_id": "INSP-HIST-2",
            "extracted_data": {
                "brand": "DemoBrand",
                "product_name": "Demo Product",
                "category": "food",
                "variant": "500g",
                "mrp": "₹60",
                "net_quantity": "500g",
                "manufacturer": "Demo Foods",
                "country_of_origin": "India",
                "date_of_manufacture": "08/2026",
                "consumer_care": "care@demo.com",
            },
            "confidence": {"mrp": 95.0, "product_name": 98.0}
        }
        resp2 = client.post("/api/compliance/evaluate", json=payload2)
        assert resp2.status_code == 200

        # 3. Query history for INSP-HIST-2
        hist_resp = client.get("/api/inspections/INSP-HIST-2/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["historical_inspections_count"] == 1
        assert hist_data["history"][0]["inspection_id"] == "INSP-HIST-1"

        # 4. Perform historical comparison for INSP-HIST-2
        comp_resp = client.post("/api/inspections/INSP-HIST-2/historical-comparison")
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["status"] == "CHANGE_DETECTED"
        assert comp_data["message"] == "Change detected — officer review recommended."
        assert any(c["field"] == "mrp" for c in comp_data["changes"])

    # ------------------ Demo Scenario Endpoints ------------------ #
    def test_list_demo_scenarios(self):
        resp = client.get("/api/demo/scenarios")
        assert resp.status_code == 200
        scenarios = resp.json()
        assert len(scenarios) == 5
        scenario_ids = [s["scenario_id"] for s in scenarios]
        assert "scenario_1" in scenario_ids
        assert "scenario_2" in scenario_ids
        assert "scenario_3" in scenario_ids
        assert "scenario_4" in scenario_ids
        assert "scenario_5" in scenario_ids

    def test_run_all_demo_scenarios(self):
        # Scenario 1 -> COMPLIANT
        r1 = client.post("/api/demo/run-scenario/scenario_1")
        assert r1.status_code == 200
        assert r1.json()["result"]["overall_status"] == "COMPLIANT"

        # Scenario 2 -> NON_COMPLIANT
        r2 = client.post("/api/demo/run-scenario/scenario_2")
        assert r2.status_code == 200
        assert r2.json()["result"]["overall_status"] == "NON_COMPLIANT"

        # Scenario 3 -> NEEDS_REVIEW
        r3 = client.post("/api/demo/run-scenario/scenario_3")
        assert r3.status_code == 200
        assert r3.json()["result"]["overall_status"] == "NEEDS_REVIEW"

        # Scenario 4 -> MISMATCH
        r4 = client.post("/api/demo/run-scenario/scenario_4")
        assert r4.status_code == 200
        assert r4.json()["result"]["overall"] == "MISMATCH"

        # Scenario 5 -> CHANGE_DETECTED
        r5 = client.post("/api/demo/run-scenario/scenario_5")
        assert r5.status_code == 200
        assert r5.json()["result"]["status"] == "CHANGE_DETECTED"

    def test_docs_and_openapi_includes_scan_endpoint(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "/api/inspection/scan" in data["paths"]
        assert "/api/scan" in data["paths"]
        assert "/api/scan/360" in data["paths"]
        assert "/api/sync" in data["paths"]

        docs_resp = client.get("/docs")
        assert docs_resp.status_code == 200

    def test_api_health_endpoint(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "SQLite"

    def test_sqlite_inspections_list_and_detail(self):
        # 1. Create inspection
        payload = {
            "category": "food",
            "inspection_id": "INSP-SQLITE-001",
            "extracted_data": {
                "product_name": "SQLite Test Biscuits",
                "mrp": "₹25",
                "net_quantity": "100g",
                "manufacturer": "Test Bakeries",
                "country_of_origin": "India",
                "date_of_manufacture": "09/2026",
                "consumer_care": "care@test.com"
            },
            "confidence": {"mrp": 95.0, "product_name": 98.0}
        }
        create_resp = client.post("/api/compliance/evaluate", json=payload)
        assert create_resp.status_code == 200

        # 2. Query list
        list_resp = client.get("/api/inspections?limit=10")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        assert any(i["inspection_id"] == "INSP-SQLITE-001" for i in list_data["inspections"])

        # 3. Query detail
        detail_resp = client.get("/api/inspections/INSP-SQLITE-001")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["inspection_id"] == "INSP-SQLITE-001"
        assert detail_data["product_name"] == "SQLite Test Biscuits"

    def test_comparison_aliases(self):
        # Comparison product alias
        comp_payload = {
            "physical_data": {"product_name": "Milk", "mrp": "₹30"},
            "online_data": {"product_name": "Milk", "mrp": "₹30"}
        }
        resp = client.post("/api/comparison/product", json=comp_payload)
        assert resp.status_code == 200
        assert resp.json()["overall"] == "MATCH"

        # Comparison history alias
        hist_payload = {
            "previous_data": {"product_name": "Milk", "mrp": "₹28"},
            "current_data": {"product_name": "Milk", "mrp": "₹30"}
        }
        h_resp = client.post("/api/comparison/history", json=hist_payload)
        assert h_resp.status_code == 200
        assert h_resp.json()["status"] == "CHANGE_DETECTED"

