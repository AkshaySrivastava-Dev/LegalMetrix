# LEGALMETRIX — Member 4: Legal Compliance + Comparison Module

AI-Assisted Legal Metrology Inspection System — Smart India Hackathon Prototype.

This module is responsible for deterministic legal rule evaluation, category rule selection, confidence-based operational routing, human review handling, physical ↔ online catalog reconciliation, and same-product historical comparison under the **Legal Metrology (Packaged Commodities) Rules, 2011**.

---

## 1. Architectural Principles & Safety Guarantees

```
                  AI / OCR Layer
                        │
                        ▼
              Extracted Information
             (Values + Confidence + Evidence)
                        │
                        ▼
              Product Category Selection
                        │
                        ▼
               RULE DATABASE (JSON)
                        │
                        ▼
             DETERMINISTIC RULE ENGINE
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
       PASS           FAIL         UNCERTAIN
         │              │              │
         │              │              ▼
         │              │        MANUAL REVIEW
         │              │        (Officer Audit)
         │              │              │
         └──────────────┴──────────────┘
                        │
                        ▼
                EVIDENCE + FINDINGS
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
      CURRENT         ONLINE        HISTORY
      PRODUCT          DATA          DATA
         │              │              │
         └──────┬───────┘              │
                ▼                      │
          RECONCILIATION               │
          (MATCH / MISMATCH)           │
                                       │
                        ┌──────────────┘
                        ▼
                 HISTORICAL DIFF
                (CHANGE DETECTED)
```

### Safety Rules:
1. **No LLM in Compliance Decisions**: AI/OCR extracts declarations and provides confidence scores. All legal compliance evaluations are strictly deterministic and rule-based.
2. **Confidence vs. Compliance Separation**:
   - **Confidence** measures *extraction reliability*.
   - **Compliance** evaluates whether the extracted information satisfies the applicable legal rule.
   - Low confidence (<60%) produces `NEEDS_REVIEW` and prompts manual verification; it is **never** automatically converted into a legal violation.
3. **No Marketplace Scraping**: Online reconciliation operates strictly against controlled mock / demo catalog payloads.
4. **Objective Terminology**: Mismatches and historical changes are reported objectively as `MISMATCH` or `CHANGE_DETECTED` with the recommendation `"Potential mismatch detected — officer review recommended."` — never labeled "illegal" without explicit deterministic statutory mandate.

---

## 2. Directory Structure

```
├── ai/
│   ├── __init__.py
│   ├── ocr_engine.py
│   ├── field_extractor.py
│   ├── pipeline.py
│   ├── image_quality.py
│   ├── multi_image.py
│   ├── category.py
│   ├── confidence.py
│   └── evidence.py
│
├── rules/
│   ├── definitions/
│   │   ├── food.json
│   │   ├── beverage.json
│   │   ├── personal_care.json
│   │   └── household.json
│   ├── schemas/
│   │   └── rule.schema.json
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── applicability.py
│   │   ├── confidence_router.py
│   │   ├── manual_review.py
│   │   ├── rule_engine.py
│   │   └── validators.py
│   └── tests/
│
├── reconciliation/
│   ├── extractor/
│   ├── normalizer/
│   ├── comparator/
│   ├── schemas/
│   └── tests/
│
├── api/
│   ├── __init__.py
│   ├── routes.py
│   ├── schemas.py
│   └── storage.py
│
├── test_data/
│   └── test_image.jpg
│
├── tests/
│   ├── test_api.py
│   ├── test_golden_scenarios.py
│   ├── test_image_inspection.py
│   └── test_real_ocr_smoke.py
│
├── main.py
└── README.md
```

---

## 3. Rule JSON Format & Category Selection

Rule sets are defined per category in JSON (`rules/definitions/{category}.json`) conforming to `rules/schemas/rule.schema.json`.

```json
{
  "category": "food",
  "version": "1.0",
  "description": "Configurable rule definition set for Food category packaged commodities",
  "rules": [
    {
      "rule_id": "RULE-FOOD-003",
      "category": "food",
      "field": "mrp",
      "required": true,
      "validation": {
        "type": "presence"
      },
      "description": "Maximum Retail Price (MRP) inclusive of all taxes must be declared",
      "source": "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(e)",
      "version": "1.0"
    }
  ]
}
```

### Supported Deterministic Validators:
- `presence`: Rejects null, empty strings, and whitespace-only strings.
- `exact`: Exact comparison (case-sensitive or case-insensitive).
- `pattern`: Regular expression format verification.
- `numeric`: Checks numeric parseability and optional bounds (`min_value`, `max_value`).
- `range`: Strict numeric interval verification (`[min_value, max_value]`).

---

## 4. Confidence Routing & Manual Review Audit Flow

```
Confidence Score:
  >= 90.0%  ──► AUTO                  (Automated evaluation permitted)
  60 - 89%  ──► REVIEW_RECOMMENDED    (Moderate certainty, optional review)
  < 60.0%   ──► MANUAL_VERIFICATION   (Mandatory officer human-in-the-loop review)
```

When an extraction falls below 60%, a pending manual review item is generated. Officers can execute:
- `CONFIRM`: Verify AI extraction is accurate.
- `CORRECT`: Provide the corrected value. **The original AI value, original confidence, and evidence reference are strictly preserved.**
- `MARK_UNREADABLE`: Flag that the label declaration is physically smudged or missing.

---

## 5. Physical ↔ Online Reconciliation

Normalizes disparate representations before comparison:
- **Price**: `₹50`, `Rs 50`, `Rs. 50.00`, `INR 50.00` $\rightarrow$ `50.00`
- **Quantity**: `500g`, `500 g`, `500 grams` $\rightarrow$ `500.0 g`; `1 kg` $\rightarrow$ `1000.0 g`; `1.5 L` $\rightarrow$ `1500.0 ml`
- **Text**: Whitespace collapsing, lowercasing, punctuation normalization.

Comparison outputs per field: `MATCH`, `MISMATCH`, or `UNAVAILABLE`.

---

## 6. Same-Product Historical Inspection Comparison

Identifies matching historical inspection records via **`brand` + `product_name` + `category` + `variant`**.
Detects declaration drifts over time (e.g. MRP increase, net quantity down-sizing) and produces `CHANGE_DETECTED` with detailed delta audit logs.

---

## 7. REST API Endpoints

The system provides standard RESTful endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `POST` | `/api/inspection/scan` | **Image-based Scan**: Uploads package image $\rightarrow$ PaddleOCR $\rightarrow$ Field Extraction $\rightarrow$ Compliance Engine |
| `POST` | `/api/compliance/evaluate` | **Structured Evaluation**: Evaluates extracted JSON declarations against deterministic rules |
| `POST` | `/api/compliance/manual-review` | Submit officer review decision (`CONFIRM` / `CORRECT` / `MARK_UNREADABLE`) |
| `POST` | `/api/reconciliation/compare` | Reconcile physical package declarations against online demo catalog |
| `GET` | `/api/inspections/{id}/history` | Retrieve previous inspection records for same product |
| `POST` | `/api/inspections/{id}/historical-comparison` | Compare current inspection against previous historical inspection |
| `GET` | `/api/demo/scenarios` | List 5 predefined SIH demo scenarios |
| `POST` | `/api/demo/run-scenario/{id}` | Execute a predefined demo scenario end-to-end |

---

## 8. Running the Backend & Swagger UI

### Start the Server:
```bash
python main.py
```
*Alternatively using uvicorn:*
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Open Swagger UI:
Navigate to: `http://localhost:8000/docs`

### Calling `/api/inspection/scan` via cURL:
```bash
curl -X POST "http://localhost:8000/api/inspection/scan" \
  -F "image=@test_data/test_image.jpg" \
  -F "category=food"
```
*(If `category` is omitted, the AI pipeline automatically classifies it from OCR keywords).*

---

## 9. Verification & Running Tests

### Automated Unit & Integration Tests:
```bash
python -m pytest -v
```
All 88 tests execute deterministically and complete in < 1 second.

### Real PaddleOCR Developer Smoke Test:
```bash
python tests/test_real_ocr_smoke.py test_data/test_image.jpg
```
Runs real PaddleOCR, extracts declarations, and evaluates compliance end-to-end.

---

## 10. Team GitHub Workflow

We follow a Pull Request workflow for multi-developer collaboration:

```
feature-branch  ──►  commit & push  ──►  Open PR  ──►  GitHub Actions (CI)  ──►  Code Review  ──►  Merge to main
```

1. **Never commit directly to `main`**.
2. **Create a feature branch**: `git checkout -b feat/your-feature-name`
3. **Run local tests**: `python -m pytest -v` (all 88 tests must pass)
4. **Push & Open PR**: Push to GitHub and open a Pull Request targeting `main`.
5. **CI Verification**: GitHub Actions automatically runs the full test suite.
6. **Code Review**: Get approval from the relevant module owner (see `.github/CODEOWNERS`).
7. **Merge & Sync**: Merge via PR, delete the feature branch, and pull latest `main`.

For detailed instructions and branch naming conventions, see [CONTRIBUTING.md](file:///c:/Users/Lenovo/OneDrive/Desktop/SIH/CONTRIBUTING.md).
