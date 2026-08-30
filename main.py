"""
LEGALMETRIX - AI-Assisted Legal Metrology Inspection System
Member 4: Legal Compliance + Comparison Engine Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from backend.routes.sync import router as sync_router
from backend.services.database_service import init_db

app = FastAPI(
    title="LegalMetrix - Legal Compliance & Comparison Engine",
    description=(
        "AI-Assisted Legal Metrology Inspection System. "
        "Provides deterministic compliance verification under Legal Metrology (Packaged Commodities) Rules, 2011, "
        "confidence routing, human-in-the-loop review audit trail, physical vs online catalog reconciliation, "
        "and same-product historical tracking."
    ),
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initializes SQLite database and tables on application startup."""
    init_db()


# Mount API & Offline Sync Routes
app.include_router(api_router)
app.include_router(sync_router)



@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "LegalMetrix Compliance & Reconciliation Engine",
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Welcome to LEGALMETRIX - AI-Assisted Legal Metrology Inspection System",
        "docs": "/docs",
        "health": "/health",
        "member": "Member 4 - Legal Compliance + Comparison Engineer",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
