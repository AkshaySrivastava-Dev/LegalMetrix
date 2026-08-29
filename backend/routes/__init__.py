# Routes package
from .scan import router as scan_router
from .compliance import router as compliance_router
from .inspections import router as inspections_router
from .sync import router as sync_router
from .comparison import router as comparison_router

__all__ = [
    "scan_router",
    "compliance_router",
    "inspections_router",
    "sync_router",
    "comparison_router",
]
