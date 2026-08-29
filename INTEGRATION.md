# Legal Metrology Backend — Complete Integration Guide

> **Author**: Member 2 (Backend + Integration Lead)  
> **Target Audience**: Frontend, AI/CV, Compliance, and Database developers.  
> **Purpose**: Complete reference for running, integrating, and testing the Legal Metrology Inspection Backend.

---

## 1. Role Boundaries & Ownership Matrix

| Area | Owner | Location | Responsibility |
|---|---|---|---|
| **Backend & Routing** | **Member 2** | `backend/main.py`, `backend/routes/` | REST APIs, CORS, upload validation, orchestration, error handling. |
| **Service Adapters** | **Member 2** | `backend/services/` | Decoupled integration adapters with mock fallbacks. |
| **AI / OCR / 360 CV** | **AI Team** | Connects to `backend/services/ai_service.py` | Text detection, NER extraction, frame sampling & multi-angle aggregation. |
| **Compliance Engine** | **Compliance Team** | Connects to `backend/services/compliance_service.py` | Legal Metrology Rules, 2011 rule verification and violation detection. |
| **Mobile Offline DB** | **Frontend Team** | Mobile Client (AsyncStorage / SQLite) | Local queueing of inspections when offline. |
| **Central Database** | **Member 2 / DB Team** | `backend/services/database_service.py` | SQLite persistence, history queries, and batch sync resolution. |

---

## 2. Complete Folder Structure

```
backend/
├── main.py                    # App entry point, CORS, routers, lifespan & health check
├── requirements.txt           # Minimal dependencies (fastapi, uvicorn, python-multipart, pydantic, pydantic-settings, httpx)
├── .env.example               # Configuration template
├── .env                       # Local environment configuration
│
├── routes/                    # HTTP API Route Controllers
│   ├── __init__.py
│   ├── scan.py                # POST /api/scan, POST /api/scan/360
│   ├── compliance.py          # POST /api/compliance
│   ├── inspections.py         # GET /api/inspection/{id}, GET /api/inspections, GET /api/inspections/same-product
│   ├── sync.py                # POST /api/sync
│   └── comparison.py          # POST /api/comparison
│
├── services/                  # Business Logic & Decoupled Integration Adapters
│   ├── __init__.py
│   ├── ai_service.py          # [ADAPTER] OCR & 360 video extraction hook
│   ├── compliance_service.py  # [ADAPTER] Legal Metrology compliance hook
│   ├── database_service.py    # [ADAPTER] SQLite storage & sync query layer
│   └── comparison_service.py  # Controlled demo catalog diff comparator
│
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic schemas (simple, intuitive field names)
│
├── utils/
│   ├── __init__.py
│   ├── files.py               # Safe upload saving, UUID naming, size/extension checks
│   └── errors.py              # Custom exceptions & structured JSON responses
│
├── data/
│   └── inspections.db         # Auto-generated SQLite database (gitignored)
│
└── uploads/
    ├── images/                # Stored inspection photos (gitignored)
    └── videos/                # Stored 360 inspection videos (gitignored)

Root files:
├── README.md                  # Project overview & quick start
├── INTEGRATION.md             # This comprehensive integration guide
├── test_backend.py            # Automated end-to-end test suite (11 test suites)
└── .gitignore                 # Excludes .env, db files, uploads, and caches
```

---

## 3. Quick Start & Execution

### Prerequisites
- Python 3.9+ (Python 3.10 recommended). No machine-specific dependencies or hardcoded paths are required.

### Installation
```bash
pip install -r backend/requirements.txt
```

### Starting the Backend
```bash
# Option 1: Using uvicorn directly (with live reload)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Running via Python module
python -m backend.main
```

### Accessing Interactive Docs
- **Swagger UI Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Alternative API Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 4. Mock Mode System

During parallel development, the backend runs independently using realistic mock fallbacks:

```env
# In backend/.env
MOCK_AI=true
MOCK_COMPLIANCE=true
```

- When `MOCK_AI=true`: The AI adapter returns realistic packaged commodity declarations (e.g., biscuits, edible oils, detergents) with bounding boxes.
- When `MOCK_COMPLIANCE=true`: The compliance adapter returns structured mock rule evaluations (`[MOCK COMPLIANCE]`).
- When real modules are ready: Set `MOCK_AI=false` and `MOCK_COMPLIANCE=false` in `.env` without modifying any route or database code.

---

## 5. Comprehensive API Endpoints Reference

### 1. `GET /api/health`
- **Purpose**: System health check, active mock mode statuses, database connectivity, and upload directory paths.
- **Request Format**: None
- **Example Response (200 OK)**:
```json
{
  "status": "ok",
  "service": "Legal Metrology Backend",
  "version": "1.0.0",
  "timestamp": "2026-08-29T15:31:34.766061Z",
  "mock_ai": true,
  "mock_compliance": true,
  "database_status": "connected",
  "uploads_dir": "C:\\Users\\ADITYA\\Desktop\\Mera Kaam\\backend\\uploads"
}
```

---

### 2. `POST /api/scan`
- **Purpose**: Core inspection flow. Receives an uploaded packaging photo, extracts declarations via AI adapter, validates compliance, saves to database, and returns the result.
- **Workflow**:
  $$\text{Image Upload} \rightarrow \text{Validation} \rightarrow \text{AI Adapter} \rightarrow \text{Compliance Adapter} \rightarrow \text{SQLite Save} \rightarrow \text{Result}$$
- **Request Format**: `multipart/form-data` with field `image`
- **Example curl**:
```bash
curl -X POST "http://localhost:8000/api/scan" \
  -F "image=@/path/to/packaging.jpg"
```
- **Example Response (200 OK)**:
```json
{
  "inspection_id": "insp_740019a98fac",
  "product_name": "Krunchy Treat Butter Cookies",
  "brand": "Britannica Foods",
  "category": "packaged_food",
  "variant": "Butter Delite 150g",
  "mrp": "₹45.00 (incl. of all taxes)",
  "net_quantity": "150 g",
  "manufacturer": "Britannica Industries Ltd., Plot 12, Industrial Area, Noida 201301",
  "confidence": 0.945,
  "compliance_status": "COMPLIANT",
  "violations": [],
  "checks": [
    {
      "field": "product_name",
      "rule": "Rule 6(1)(a) - Name / Generic Identity",
      "passed": true,
      "detected_value": "Krunchy Treat Butter Cookies",
      "message": "Product identity clearly declared."
    }
  ],
  "evidence": {
    "mrp_bbox": [120, 340, 260, 370]
  },
  "source": "image",
  "sync_status": "synced",
  "created_at": "2026-08-29T15:35:10.070123Z",
  "file_path": "backend/uploads/images/774d9a570e394ac899de50182b96045a.png"
}
```
- **Error Responses**:
  - `400 Bad Request`: Empty file or unsupported format (`.txt`, `.pdf`).

---

### 3. `POST /api/scan/360`
- **Purpose**: Ingests a continuous rotational video scan of a package to analyze multiple panels.
- **Workflow**:
  $$\text{Video Upload} \rightarrow \text{ai\_service.analyze\_video()} \rightarrow \text{Compliance Adapter} \rightarrow \text{SQLite Save} \rightarrow \text{Result}$$
- **Architecture Note**: **NO 3D reconstruction** or complicated computer vision pipeline is built in the backend. The backend delegates video processing directly to `ai_service.analyze_video()`.
- **Request Format**: `multipart/form-data` with field `video`
- **Example curl**:
```bash
curl -X POST "http://localhost:8000/api/scan/360" \
  -F "video=@/path/to/rotation.mp4"
```
- **Example Response (200 OK)**:
```json
{
  "inspection_id": "insp_5176490a2b06",
  "product_name": "Krunchy Treat Butter Cookies",
  "brand": "Britannica Foods",
  "confidence": 0.96,
  "compliance_status": "COMPLIANT",
  "source": "video_360",
  "evidence": {
    "angles_scanned": 12,
    "front_panel_confidence": 0.98,
    "back_panel_confidence": 0.96
  }
}
```

---

### 4. `POST /api/compliance`
- **Purpose**: Direct evaluation of product metadata without uploading a new image.
- **Request Format**: `application/json`
- **Example Request**:
```json
{
  "product_name": "Nutri Crunch Wheat Bread",
  "brand": "Healthy Bakers",
  "mrp": "₹40.00 (incl. of all taxes)",
  "net_quantity": "400 g",
  "manufacturer": "Healthy Bakers Pvt Ltd, New Delhi 110020"
}
```
- **Example Response (200 OK)**:
```json
{
  "compliance_status": "COMPLIANT",
  "confidence": 0.95,
  "checks": [
    {
      "field": "product_name",
      "rule": "Rule 6(1)(a) - Name / Generic Identity",
      "passed": true,
      "detected_value": "Nutri Crunch Wheat Bread",
      "message": "Product identity clearly declared."
    }
  ],
  "violations": [],
  "summary": "[MOCK COMPLIANCE] All mandatory Legal Metrology declarations verified successfully."
}
```

---

### 5. `GET /api/inspection/{id}`
- **Purpose**: Retrieve complete details of a previously saved inspection by its unique `inspection_id`.
- **Example Response (200 OK)**: Full `InspectionResponse` JSON object.
- **Error Response**: `404 Not Found` if the inspection record does not exist.

---

### 6. `GET /api/inspections`
- **Purpose**: Retrieve paginated inspection history with optional filtering.
- **Query Parameters**:
  - `limit` (integer, default 50)
  - `offset` (integer, default 0)
  - `compliance_status` (optional string, e.g., `COMPLIANT`, `NON_COMPLIANT`)
  - `sync_status` (optional string, e.g., `synced`, `pending`)
- **Example Response (200 OK)**:
```json
{
  "total": 14,
  "items": [
    {
      "inspection_id": "insp_740019a98fac",
      "product_name": "Krunchy Treat Butter Cookies",
      "brand": "Britannica Foods",
      "compliance_status": "COMPLIANT",
      "created_at": "2026-08-29T15:35:10.070123Z"
    }
  ]
}
```

---

### 7. `GET /api/inspections/same-product`
- **Purpose**: Look up past inspections for identical or related products.
- **Query Parameters**: `brand`, `product_name`, `category`, `variant`, `limit`.
- **Example Request**:
```
GET /api/inspections/same-product?brand=Britannica%20Foods
```
- **Example Response (200 OK)**: Array of matching `InspectionResponse` objects.

---

### 8. `POST /api/sync`
- **Purpose**: Synchronize inspection records collected offline by mobile devices when connectivity is restored.
- **Offline Architecture Flow**:
  $$\text{Phone Local Storage (Offline)} \xrightarrow{\text{Internet Restored}} \text{POST /api/sync} \rightarrow \text{Central SQLite DB}$$
  *(Note: Phone-side local caching is handled on the mobile device. The backend provides safe, idempotent synchronization).*
- **Duplicate & Error Handling**:
  - Existing `inspection_id` records are updated safely (`"action": "updated"`).
  - New records are created (`"action": "created"`).
  - Malformed records fail individually without aborting or crashing the rest of the batch.
- **Request Format**: `application/json`
- **Example Request**:
```json
{
  "records": [
    {
      "inspection_id": "offline_uuid_001",
      "product_name": "Organic Almonds",
      "brand": "Natures Best",
      "category": "dry_fruits",
      "mrp": "₹250.00",
      "net_quantity": "200 g",
      "manufacturer": "Natures Best Organics, Mumbai 400001",
      "compliance_status": "COMPLIANT",
      "source": "mobile_offline"
    }
  ]
}
```
- **Example Response (200 OK)**:
```json
{
  "total_received": 1,
  "synced_count": 1,
  "failed_count": 0,
  "results": [
    {
      "inspection_id": "offline_uuid_001",
      "status": "synced",
      "action": "created",
      "reason": "Successfully synchronized"
    }
  ]
}
```

---

### 9. `POST /api/comparison`
- **Purpose**: Compare physical pack declarations against controlled online reference catalog listings to detect discrepancies (e.g., price gouging / MRP alterations).
- **Architecture Note**: **NO external website scraping** (Amazon/Flipkart). Operates strictly on verified reference catalog data for reliable offline/demo execution.
- **Request Format**: `application/json` (pass `inspection_id` or direct product fields)
- **Example Request**:
```json
{
  "brand": "Dhara Agro",
  "product_name": "Pure Gold Refined Mustard Oil",
  "mrp": "₹190.00",
  "net_quantity": "1 L / 910 g"
}
```
- **Example Response (200 OK)**:
```json
{
  "status": "mismatched",
  "product_name": "Pure Gold Refined Mustard Oil",
  "brand": "Dhara Agro",
  "matched_fields": ["brand", "product_name", "net_quantity", "manufacturer"],
  "mismatched_fields": ["mrp"],
  "details": [
    {
      "field": "Maximum Retail Price (MRP)",
      "physical_value": "₹190.00",
      "online_value": "₹160.00",
      "matched": false,
      "note": "Discrepancy detected between physical packaging and online benchmark."
    }
  ],
  "online_source": "Controlled Demo Catalog",
  "message": "Discrepancies identified in 1 field(s) (e.g. mrp)."
}
```

---

## 6. Frontend Developer Integration Examples

### A. Photo Scan (`POST /api/scan`)
```javascript
// JavaScript / TypeScript Fetch Example
async function scanPackagePhoto(imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch("http://localhost:8000/api/scan", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || "Failed to scan image");
  }

  const result = await response.json();
  console.log("Inspection ID:", result.inspection_id);
  console.log("Status:", result.compliance_status);
  return result;
}
```

### B. 360 Video Scan (`POST /api/scan/360`)
```javascript
async function scanPackageVideo(videoFile) {
  const formData = new FormData();
  formData.append("video", videoFile);

  const response = await fetch("http://localhost:8000/api/scan/360", {
    method: "POST",
    body: formData,
  });

  return await response.json();
}
```

### C. Offline Batch Sync (`POST /api/sync`)
```javascript
async function syncOfflineRecords(cachedRecords) {
  const response = await fetch("http://localhost:8000/api/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ records: cachedRecords }),
  });

  const syncResult = await response.json();
  console.log(`Synced ${syncResult.synced_count} records.`);
  return syncResult;
}
```

---

## 7. AI / OCR Module Integration Guide

- **File to Modify**: [`backend/services/ai_service.py`](file:///c:/Users/ADITYA/Desktop/Mera%20Kaam/backend/services/ai_service.py)
- **Functions to Connect**:
  1. `analyze_image(file_path: str) -> AIAnalysisResult`
  2. `analyze_video(file_path: str) -> AIAnalysisResult`
- **Instructions**:
  - Replace the internal stub in `analyze_image` with your OCR / entity extraction call.
  - Set `MOCK_AI=false` in `backend/.env`.
  - **No changes to routes or databases are required.**

---

## 8. Compliance Engine Integration Guide

- **File to Modify**: [`backend/services/compliance_service.py`](file:///c:/Users/ADITYA/Desktop/Mera%20Kaam/backend/services/compliance_service.py)
- **Function to Connect**:
  - `check_compliance(data: Union[AIAnalysisResult, ComplianceRequest, Dict[str, Any]]) -> ComplianceResult`
- **Instructions**:
  - Call your custom Legal Metrology rule engine inside `check_compliance`.
  - Return a `ComplianceResult` object with `compliance_status` (`COMPLIANT`, `NON_COMPLIANT`, `PARTIALLY_COMPLIANT`), `checks`, and `violations`.
  - Set `MOCK_COMPLIANCE=false` in `backend/.env`.
  - **No changes to routes or databases are required.**

---

## 9. Database Architecture & Operations

- **Storage Engine**: SQLite file located at `backend/data/inspections.db` (auto-initialized on startup).
- **Service Layer**: All operations are encapsulated inside [`backend/services/database_service.py`](file:///c:/Users/ADITYA/Desktop/Mera%20Kaam/backend/services/database_service.py):
  - `save_inspection(...)`
  - `get_inspection(inspection_id)`
  - `get_inspections(limit, offset, compliance_status, sync_status)`
  - `get_same_product(brand, product_name, category, variant)`
  - `process_sync_batch(records)`
- **Route Isolation**: Routes contain **zero raw SQL queries**.

---

## 10. Verification & Test Suite

Run the automated test suite to verify all 11 endpoints and integration workflows:

```bash
python test_backend.py
```

*Expected output*: **`ALL 11 TEST SUITES PASSED PERFECTLY!`**
