"""Dev helper: snapshot of loaded env for Settings UI autofill (admin-only when enabled)."""
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter()


async def require_enabled_env_template_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """404 when disabled (after auth, so non-admins do not learn admin-only vs missing)."""
    if not settings.ENABLE_ENV_TEMPLATE_ENDPOINT:
        raise HTTPException(status_code=404, detail="Endpoint disabled")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/settings/env-template")
async def env_template(_admin: User = Depends(require_enabled_env_template_admin)):
    """Return backend .env-derived values for Settings UI. Requires admin when flag is on."""
    s = settings
    cors_str = ",".join(s.CORS_ORIGINS) if isinstance(s.CORS_ORIGINS, list) else str(s.CORS_ORIGINS or "")

    return {
        "llmProvider": s.LLM_PROVIDER,
        "llmModel": s.LLM_MODEL or "",
        "llmFastModel": s.LLM_FAST_MODEL or "",
        "orchestrationUseLlm": s.ORCHESTRATION_USE_LLM,
        "openaiApiKey": s.OPENAI_API_KEY or "",
        "openaiModel": s.OPENAI_MODEL,
        "anthropicApiKey": s.ANTHROPIC_API_KEY or "",
        "geminiApiKey": s.GEMINI_API_KEY or "",
        "langsmithApiKey": s.LANGSMITH_API_KEY or "",
        "langsmithProject": s.LANGSMITH_PROJECT or "",
        "langsmithTracing": s.LANGSMITH_TRACING,
        "databaseUrl": s.DATABASE_URL,
        "redisUrl": s.REDIS_URL,
        "secretKey": s.SECRET_KEY,
        "googleClientIdBackend": s.GOOGLE_CLIENT_ID or "",
        "googleClientSecret": s.GOOGLE_CLIENT_SECRET or "",
        "googleRedirectUri": s.GOOGLE_REDIRECT_URI,
        "frontendUrl": s.FRONTEND_URL,
        "corsOrigins": cors_str,
    }
