"""Fernet encryption for at-rest user LLM credentials."""
from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """
    Fernet key: set LLM_CREDENTIALS_FERNET_KEY to a urlsafe base64-encoded 32-byte key
    (generate once: ``python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"``).

    If unset, derives a key from SECRET_KEY (rotation of SECRET_KEY invalidates stored credentials).
    """
    raw = settings.LLM_CREDENTIALS_FERNET_KEY
    if isinstance(raw, str) and raw.strip():
        key = raw.strip().encode("ascii")
        return Fernet(key)

    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    text = plaintext.strip()
    if not text:
        return None
    token = _fernet().encrypt(text.encode("utf-8"))
    return token.decode("ascii")


def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext or not str(ciphertext).strip():
        return None
    try:
        return _fernet().decrypt(str(ciphertext).strip().encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Failed to decrypt LLM credential (wrong key or corrupt data)")
        return None
