"""Dev helper: snapshot of loaded env for Settings UI autofill."""
from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter()


@router.get("/settings/env-template")
async def env_template():
    """Return backend .env-derived values (camelCase) for browser Settings form. Gated by config."""
    if not settings.ENABLE_ENV_TEMPLATE_ENDPOINT:
        raise HTTPException(status_code=404, detail="Endpoint disabled")

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
