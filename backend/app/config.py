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
    
    # OpenAI / LLM
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # LangSmith
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: Optional[str] = "inboxpilot-ai"
    LANGSMITH_TRACING: bool = True
    
    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Application Settings
    CONFIDENCE_THRESHOLD: float = 0.7
    MAX_MESSAGE_LENGTH: int = 10000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
