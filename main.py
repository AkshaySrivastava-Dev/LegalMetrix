"""
LEGALMETRIX - AI-Assisted Legal Metrology Inspection System
Unified Backend Entry Point (Member 2 Integration & Sync + Member 4 Compliance & Reconciliation).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.storage import db
from utils.files import ensure_upload_dirs
from utils.errors import AppException, app_exception_handler, global_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure upload directories and SQLite tables exist
    ensure_upload_dirs()
    db._init_sqlite()
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="LegalMetrix - AI-Assisted Legal Metrology Inspection System",
    description=(
        "Unified Legal Metrology Inspection & Synchronization Backend. "
        "Provides deterministic compliance verification under Legal Metrology (Packaged Commodities) Rules, 2011, "
        "AI OCR extraction, multi-panel 360 video inspection, confidence routing, offline batch synchronization, "
        "human-in-the-loop review audit trail, and physical vs online catalog reconciliation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Mount API Routes
app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "LegalMetrix Unified Backend",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to LEGALMETRIX - AI-Assisted Legal Metrology Inspection System",
        "docs": "/docs",
        "health": "/health",
        "api_health": "/api/health",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
