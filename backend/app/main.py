"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.rate_limit import SLOWAPI_ENABLED, limiter

setup_logging()
logger = logging.getLogger(__name__)
from app.database import init_db

_WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "changeme",
        "secret",
        "dev",
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate security in production, then initialize database (non-fatal on DB errors)."""
    if settings.ENVIRONMENT.lower() == "production":
        sk = settings.SECRET_KEY.strip()
        if len(sk) < 32 or sk.lower() in _WEAK_SECRET_KEYS:
            raise RuntimeError(
                "Production requires a strong SECRET_KEY (32+ characters, not a default). "
                "Set SECRET_KEY in the environment."
            )
        if settings.REQUIRE_SLOWAPI_IN_PRODUCTION and not SLOWAPI_ENABLED:
            raise RuntimeError(
                "Production requires rate limiting. Install slowapi (pip install slowapi==0.1.9) "
                "or set REQUIRE_SLOWAPI_IN_PRODUCTION=false only for non-internet-facing debug."
            )
    try:
        init_db()
    except Exception:
        logger.exception(
            "Database init failed (check DATABASE_URL / Cloud SQL). "
            "Service is up; DB-backed routes will error until the database is reachable."
        )
    yield


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    lifespan=lifespan,
)

if SLOWAPI_ENABLED:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
else:
    logger.warning(
        "slowapi is not installed — rate limiting is disabled. "
        "Install with: pip install slowapi==0.1.9"
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "InboxPilot AI API",
        "version": settings.VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Import API routes
from app.api.v1.router import router as api_router

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
