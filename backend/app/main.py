"""FastAPI application entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
from app.database import init_db

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup (non-fatal so Cloud Run can bind PORT if DB is misconfigured)."""
    try:
        init_db()
    except Exception:
        logger.exception(
            "Database init failed (check DATABASE_URL / Cloud SQL). "
            "Service is up; DB-backed routes will error until the database is reachable."
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "InboxPilot AI API",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import API routes
from app.api.v1.router import router as api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
