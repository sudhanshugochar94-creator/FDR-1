from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.documents import router as documents_router
from app.api.fdrs import router as fdrs_router
from app.api.institutions import router as institutions_router
from app.api.workflows import router as workflows_router
from app.api.ai import router as ai_router
from app.api.notifications import router as notifications_router
from app.api.reports import router as reports_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "documents_router",
    "fdrs_router",
    "institutions_router",
    "workflows_router",
    "ai_router",
    "notifications_router",
    "reports_router",
]
