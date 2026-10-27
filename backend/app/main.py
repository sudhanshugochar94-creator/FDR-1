import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import (
    ai_router,
    auth_router,
    dashboard_router,
    documents_router,
    fdrs_router,
    institutions_router,
    notifications_router,
    reports_router,
    workflows_router,
)
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app import database
import app.models  # noqa: F401 - Register all models for SQLAlchemy mapper resolution


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await database.initialize_database()
    yield


app = FastAPI(
    title="FDR Intelligence & Compliance Portal API",
    description="Backend API for AI-assisted Fixed Deposit Receipt (FDR) verification, extraction, and lifecycle compliance monitoring.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register application exception handlers
register_exception_handlers(app)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(fdrs_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(institutions_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(reports_router, prefix="/api")


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "fdr-portal-backend",
        "version": "1.0.0",
        "database": database.database_backend,
        "local_database_fallback": database.using_local_fallback,
    }
