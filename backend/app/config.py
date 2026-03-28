"""Configuration management for InboxPilot AI."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "InboxPilot AI"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/inboxpilot"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM: set LLM_PROVIDER and LLM_MODEL; OPENAI_* kept for backward compatibility.
    # LLM_PROVIDER: openai | anthropic | google_genai
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: Optional[str] = None  # Defaults to OPENAI_MODEL when unset (OpenAI path)
    # Optional cheaper model for classify / extract / confidence (ignored when unset; see llm_utils).
    LLM_FAST_MODEL: Optional[str] = None
    # When False (default), route specialists from classify_intent only (no extra LLM call).
    ORCHESTRATION_USE_LLM: bool = False
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    # Gemini (Google AI Studio) — not the same as Gmail OAuth client secret
    GEMINI_API_KEY: Optional[str] = None
    
    # LangSmith
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: Optional[str] = "inboxpilot-ai"
    LANGSMITH_TRACING: bool = True
    
    # deployment / hardening
    ENVIRONMENT: str = "development"
    # When False, OpenAPI /docs and /redoc are disabled (recommended for production).
    DOCS_ENABLED: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Guest bootstrap JWT lifetime (browser sessions without Google sign-in).
    GUEST_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth (Gmail)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/gmail/oauth/callback"

    # After the user completes Gmail OAuth in the browser, the backend callback endpoint
    # should redirect the browser back to the frontend so the UI can refresh state.
    #
    # Local dev: Next.js usually runs on http://localhost:3002
    FRONTEND_URL: str = "http://localhost:3002"
    
    # CORS
    # Dev: Next.js often increments ports (3000, 3001, 3002, ...). Add the expected ports here.
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]
    
    # Application Settings
    CONFIDENCE_THRESHOLD: float = 0.7
    MAX_MESSAGE_LENGTH: int = 10000

    # When True, GET /api/v1/settings/env-template returns values loaded from backend .env (for Settings UI).
    # Default False — enable only on trusted local dev (exposes secrets).
    ENABLE_ENV_TEMPLATE_ENDPOINT: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
