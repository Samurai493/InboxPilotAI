"""Shared rate limiter; uses SlowAPI when installed, otherwise no-op decorators."""
from __future__ import annotations

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    SLOWAPI_ENABLED = True
except ImportError:  # pragma: no cover - optional dependency

    class _NoOpLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator

    limiter = _NoOpLimiter()
    SLOWAPI_ENABLED = False
