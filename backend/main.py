"""
Legal Metrology Inspection Backend - Main Application Entrypoint
FastAPI server orchestrating AI extraction, Compliance Rules, SQLite persistence, Offline Sync, and Comparisons.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.schemas import HealthResponse
from .utils.errors import AppException, app_exception_handler, global_exception_handler
from .utils.files import ensure_upload_dirs, get_upload_base_dir
from .services.database_service import init_db
from .services.ai_service import is_mock_ai_enabled
from .services.compliance_service import is_mock_compliance_enabled

from .routes.scan import router as scan_router
from .routes.compliance import router as compliance_router
from .routes.inspections import router as inspections_router
from .routes.sync import router as sync_router
from .routes.comparison import router as comparison_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("legal_metrology.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    logger.info("Starting Legal Metrology Inspection Backend...")
    # 1. Initialize SQLite Database tables
    init_db()
    # 2. Ensure media upload directories exist
    ensure_upload_dirs()
    logger.info("Backend initialized and ready to serve requests.")
    yield
    logger.info("Shutting down Legal Metrology Inspection Backend.")


# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered Legal Metrology Inspection API",
    description="Backend integration layer for packaged commodities inspection under Legal Metrology Rules, 2011.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local mobile & web frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Mount Routers
app.include_router(scan_router)
app.include_router(compliance_router)
app.include_router(inspections_router)
app.include_router(sync_router)
app.include_router(comparison_router)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health & System"],
    summary="System Health Check",
)
async def health_check():
    """Returns current system health, active mock modes, and storage status."""
    return HealthResponse(
        status="ok",
        service="Legal Metrology Backend",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        mock_ai=is_mock_ai_enabled(),
        mock_compliance=is_mock_compliance_enabled(),
        database_status="connected",
        uploads_dir=str(get_upload_base_dir()),
    )


@app.get("/", tags=["Health & System"], include_in_schema=False)
async def root():
    """Root landing endpoint with interactive documentation link."""
    return {
        "message": "Legal Metrology Inspection Backend is running.",
        "documentation": "/docs",
        "health_check": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
