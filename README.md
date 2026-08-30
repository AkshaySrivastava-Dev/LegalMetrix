# LEGALMETRIX — Integrated AI-Assisted Legal Metrology Inspection System

> **Smart India Hackathon (SIH) — Production-Grade Integrated Solution**
> Central Repository: [https://github.com/AkshaySrivastava-Dev/LegalMetrix.git](https://github.com/AkshaySrivastava-Dev/LegalMetrix.git)

---

## 1. Executive Summary & Problem Statement

**LegalMetrix** is an end-to-end, multi-tier inspection and compliance platform designed for enforcement officers under the **Legal Metrology (Packaged Commodities) Rules, 2011**.

In physical markets and e-commerce distribution centers, verifying mandatory packaged commodity declarations (MRP, Net Quantity, Manufacturer/Packer Address, Country of Origin, Manufacturing/Expiry Dates, Consumer Care) is labor-intensive and prone to human error.

LegalMetrix solves this through:
1. **NVIDIA Nemotron OCR v2 Cloud Engine** for millisecond-speed, high-accuracy text extraction from single images and 360-degree rotation scans.
2. **Deterministic Legal Metrology Rule Engine** ensuring statutory compliance is verified with 100% mathematical consistency without LLM hallucination.
3. **Authoritative SQLite Persistence** providing thread-safe, local and edge-first data storage.
4. **IndexedDB & SyncManager Offline Architecture** enabling seamless field operations in connectivity-constrained rural markets with automated idempotent syncing.
5. **Reconciliation & Historical Tracking** detecting physical vs online price discrepancy and shrinkflation.
6. **Multi-Lingual Voice Assistant** supporting English, Hindi, and Telugu guidance.

---

## 2. Integrated System Architecture

```
                               ┌────────────────────────┐
                               │   FRONTEND INTERFACE   │
                               │  (Dashboard / Voice)   │
                               └───────────┬────────────┘
                                           │
                      ┌────────────────────┴────────────────────┐
                      │                                         │
             [Online Connection]                               [Offline Field Operation]
                      │                                         │
                      ▼                                         ▼
            FastAPI Backend Gateway                       IndexedDB Storage
          (POST /api/scan, /api/sync)                     (Offline Records)
                      │                                         │
       ┌──────────────┴──────────────┐                          ▼
       ▼                             ▼                     SyncManager
Single Image Scan             360 Video Scan             (Batch Upsert Queue)
(Quality & Preprocess)       (Keyframe Rotation)                │
       │                             │                          │
       └──────────────┬──────────────┘                          │
                      ▼                                         │
         NVIDIA Nemotron OCR v2 API                             │
         (Cloud Detections & BBoxes)                            │
                      │                                         │
                      ▼                                         │
            Field Extraction Engine                             │
          (MRP, Qty, Dates, Address)                            │
                      │                                         │
                      ▼                                         │
         Deterministic Rule Engine                              │
        (Rule Database: JSON Schemas)                           │
                      │                                         │
       ┌──────────────┼──────────────┐                          │
       ▼              ▼              ▼                          │
     PASS           FAIL         UNCERTAIN                      │
       │              │        (Needs Review)                   │
       │              │              │                          │
       └──────────────┴──────┬───────┘                          │
                             ▼                                  │
                    Officer Audit Trail                         │
                             │                                  │
                             ▼                                  │
               Authoritative SQLite DB <────────────────────────┘
                 (data/inspections.db)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Reconciliation Engine             Historical Comparison
 (Physical vs Online Delta)         (Shrinkflation & Price Hike)
```

---

## 3. Team Member Modules & Responsibilities

| Contributor | Domain & Responsibility | Key Components |
|---|---|---|
| **Akshay** | Legal Metrology Rules & Integration | Deterministic Rule Engine, JSON Schemas (`food.json`, `beverage.json`, `personal_care.json`, `household.json`), Compliance Validators, Confidence Router |
| **Aditya1127git** | FastAPI Backend & Persistence | API Gateway (`api/routes.py`), SQLite Service (`backend/services/database_service.py`), Upload Validation, Reconciliation & Comparison Routes |
| **Pawan** | AI & OCR Pipeline | NVIDIA Nemotron OCR v2 Client (`ai/nvidia_ocr.py`), Image Preprocessing, Quality Scoring, Field Extractor, Category Classifier, Multi-Image Fusion |
| **Akshat** | Offline Database, Sync & Voice | IndexedDB Engine (`src/db/indexedDB.js`), SyncManager Client (`src/sync/syncManager.js`), SQLite Sync Client (`src/db/sqliteClient.js`), Voice Assistant (`src/voice/voiceAssistant.js`) |
| **Aditya Rathod** | Frontend UI & Interactive Dashboard | Modern Web App (`demo/index.html`), SmartScan Camera, 360 Scan Viewer, OCR Review, Manual Correction, Analytics & Report Generator |

---

## 4. Key Architectural Guarantees & Safeguards

### A. Production OCR vs Legacy
- **Production Engine**: **NVIDIA Nemotron OCR v2** (`https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2`) handles all high-accuracy production text detection and bounding-box spatial coordinates.
- **PaddleOCR Status**: Marked strictly as legacy/development fallback. It is completely decoupled from the production cloud pipeline.
- **Missing API Keys**: If `NVIDIA_API_KEY` is not provided in a live scan, the system returns a controlled error/review state rather than fabricating declarations.

### B. Authoritative Backend Database
- **Production Database**: **SQLite** (`data/inspections.db`). Fully thread-safe, initialized on startup via `init_db()`, indexed on `inspection_id`, `created_at`, and `product_name`.
- **Supabase Status**: Not part of the architecture and removed from all production execution paths.

### C. Deterministic Compliance Verification
- The AI/OCR module **extracts declarations only**.
- The Legal Metrology Rules Engine **alone** decides compliance.
- No LLM hallucination or probabilistic guesswork in statutory violation tagging.
- Zero fabrication: If a declaration is unreadable or smudged, it is marked `NEEDS_REVIEW` and flagged for manual officer audit.

---

## 5. API Reference Summary

### Core Scanning & Compliance
- `POST /api/scan` — Upload packaging photo (JPEG/PNG/WebP), runs NVIDIA OCR, extracts declarations, evaluates rules, saves to SQLite, returns full compliance breakdown.
- `POST /api/scan/360` — Upload continuous rotation video or multi-view capture, samples keyframes, fuses multi-panel text, verifies compliance.
- `POST /api/inspection/scan` — Standard endpoint alias for `/api/scan`.
- `POST /api/compliance/evaluate` — Direct structured JSON compliance evaluation (used for manual entry and testing).
- `POST /api/compliance/manual-review` — Officer human-in-the-loop audit decision (`CONFIRM`, `CORRECT`, `MARK_UNREADABLE`).

### Offline Synchronization
- `POST /api/sync` — Offline batch ingestion endpoint for client-side IndexedDB records with idempotent SQLite upsert.

### Inspection History & Reconciliation
- `GET /api/inspections` — List persisted inspections with pagination (`limit`, `offset`, `compliance_status`, `sync_status`).
- `GET /api/inspections/{inspection_id}` — Get single inspection details.
- `GET /api/inspections/{inspection_id}/history` — Retrieve past records for the same product.
- `POST /api/inspections/{inspection_id}/historical-comparison` — Compare current inspection against previous baseline (shrinkflation/MRP hike).
- `POST /api/reconciliation/compare` (Alias: `/api/comparison/product`) — Reconcile physical package vs online listing.
- `POST /api/comparison/history` — Historical comparison alias.

### Demonstration & System
- `GET /health` & `GET /api/health` — System health and readiness checks.
- `GET /api/demo/scenarios` — List 5 predefined SIH demo scenarios.
- `POST /api/demo/run-scenario/{id}` — Execute predefined demo scenario.

---

## 6. Directory Structure

```
LegalMetrix/
├── ai/                         # AI & OCR Pipeline
│   ├── nvidia_ocr.py           # NVIDIA Nemotron OCR v2 Client
│   ├── ocr_engine.py           # Unified OCR Engine Wrapper
│   ├── preprocess.py           # Image preprocessing & contrast enhancement
│   ├── image_quality.py        # Resolution, blur, and brightness validator
│   ├── field_extractor.py      # Regex & heuristic declaration parser
│   ├── category.py             # Packaging commodity classifier
│   ├── confidence.py           # Confidence scoring & tiered routing
│   ├── multi_image.py          # Multi-view and 360 fusion logic
│   ├── business_rules.py       # Brand canonicalization (non-fabricating)
│   ├── evidence.py             # Bounding box & crop evidence generator
│   └── pipeline.py             # End-to-end InspectionAI pipeline
│
├── rules/                      # Deterministic Legal Metrology Engine
│   ├── definitions/            # JSON Statutory Rules (Food, Beverage, etc.)
│   ├── schemas/                # Rule schema definitions
│   ├── engine/                 # Applicability, router, validators, engine
│   └── tests/                  # Rules test suite
│
├── reconciliation/             # Comparison & Reconciliation
│   ├── comparator.py           # Product & historical comparator
│   ├── normalizer/             # Price, quantity, and text normalizers
│   └── tests/                  # Reconciliation test suite
│
├── backend/                    # Backend Support & Database Service
│   ├── routes/                 # Sync route definitions
│   └── services/               # Authoritative SQLite database service
│
├── api/                        # FastAPI REST Route Handlers
│   ├── routes.py               # Complete unified API endpoints
│   ├── schemas.py              # Pydantic request/response schemas
│   └── storage.py              # In-memory repository & cache adapter
│
├── src/                        # Frontend Offline & Client Subsystems
│   ├── db/                     # IndexedDB & SQLite sync client
│   ├── sync/                   # SyncManager queue & retry engine
│   ├── history/                # History comparison utilities
│   ├── voice/                  # Speech synthesis & multi-lingual assistant
│   └── data/                   # Mock scenarios & test data
│
├── demo/                       # Interactive Frontend UI
│   └── index.html              # Full officer inspection dashboard
│
├── tests/                      # Automated Test Suite
│   ├── test_api.py             # REST API endpoint tests
│   ├── test_golden_scenarios.py# SIH golden path tests
│   ├── test_image_inspection.py# Image scan tests
│   ├── test_sync.py            # Offline sync tests
│   ├── test_ai_ocr.py          # AI & OCR pipeline tests
│   ├── testRunner.ps1          # 13-scenario automated test runner
│   └── testRunner.js           # JavaScript test runner
│
├── main.py                     # Primary FastAPI Application Entrypoint
├── requirements.txt            # Python Core Dependencies
├── requirements-dev.txt        # Development & Test Dependencies
├── package.json                # Frontend Scripts & Metadata
├── .env.example                # Environment Variable Template
├── .gitignore                  # Git Ignore Rules
└── README.md                   # Authoritative Documentation
```

---

## 7. Installation & Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ (optional, for frontend serving)
- NVIDIA API Key (for live cloud OCR)

### Backend Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/AkshaySrivastava-Dev/LegalMetrix.git
   cd LegalMetrix
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate      # Windows
   # source .venv/bin/activate   # Linux/macOS
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and supply your NVIDIA_API_KEY if testing cloud OCR
   ```
5. Start the FastAPI backend server:
   ```bash
   python main.py
   ```
   Backend will be active at `http://localhost:8000`.  
   Interactive Swagger API Documentation: `http://localhost:8000/docs`.

### Frontend Setup & Demo
1. Serve the frontend application:
   ```bash
   npx serve .
   ```
2. Open `http://localhost:3000/demo/index.html` in a web browser.
3. Use the top toggle to switch between **Online** and **Offline (Field Mode)** to test IndexedDB caching and automated synchronization with FastAPI SQLite.

---

## 8. Running Automated Tests

### Python Test Suite (111 Tests)
Execute the complete backend, AI, rules, reconciliation, and sync test suite:
```bash
python -m pytest -v
```

### Scenario Test Suite (13 Scenarios)
Execute the 13 SIH scenario checks:
```bash
powershell -ExecutionPolicy Bypass -File ./tests/testRunner.ps1
```

---

## 9. Security & Compliance Safeguards
- **Zero Secrets**: `.env` files, credentials, and API keys are strictly excluded via `.gitignore`.
- **Upload Hardening**: File size limits (15MB images, 100MB video), MIME checking, and UUID-based temporary file handling.
- **Audit Trails**: Every manual review records the Officer ID, timestamp, original AI value, corrected value, and explanation notes for full legal defensibility.

---
*LegalMetrix — Built for Smart India Hackathon (SIH 2026).*
