"""Load and save encrypted user LLM API keys."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.user_llm_credential import UserLlmCredential
from app.services.gmail_oauth import require_user_uuid
from app.services.secret_crypto import decrypt_secret, encrypt_secret


def _uid(user_id: str) -> uuid.UUID:
    return require_user_uuid(user_id)


def get_row(db: Session, user_id: str) -> UserLlmCredential | None:
    uid = _uid(user_id)
    return db.query(UserLlmCredential).filter(UserLlmCredential.user_id == uid).first()


def get_decrypted_keys(db: Session, user_id: str) -> dict[str, str | None]:
    row = get_row(db, user_id)
    if not row:
        return {"openai_api_key": None, "anthropic_api_key": None, "gemini_api_key": None}
    return {
        "openai_api_key": decrypt_secret(row.encrypted_openai_key),
        "anthropic_api_key": decrypt_secret(row.encrypted_anthropic_key),
        "gemini_api_key": decrypt_secret(row.encrypted_gemini_key),
    }


def get_public_status(db: Session, user_id: str) -> dict[str, Any]:
    """Which slots have a stored secret (no lengths or ciphertext)."""
    row = get_row(db, user_id)
    if not row:
        return {
            "has_openai": False,
            "has_anthropic": False,
            "has_gemini": False,
        }
    return {
        "has_openai": bool(row.encrypted_openai_key and str(row.encrypted_openai_key).strip()),
        "has_anthropic": bool(row.encrypted_anthropic_key and str(row.encrypted_anthropic_key).strip()),
        "has_gemini": bool(row.encrypted_gemini_key and str(row.encrypted_gemini_key).strip()),
    }


def save_credentials(
    db: Session,
    user_id: str,
    *,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    gemini_api_key: str | None = None,
    clear_openai: bool = False,
    clear_anthropic: bool = False,
    clear_gemini: bool = False,
) -> UserLlmCredential:
    """
    Upsert row. Pass ``clear_*`` to remove a slot. Plain values encrypt to ciphertext; empty string clears.
    Use ``None`` for a field to leave existing DB value unchanged.
    """
    uid = _uid(user_id)
    row = get_row(db, user_id)
    if not row:
        row = UserLlmCredential(user_id=uid)
        db.add(row)

    def apply_field(
        enc_col: str,
        plain: str | None,
        clear: bool,
    ) -> None:
        if clear:
            setattr(row, enc_col, None)
            return
        if plain is None:
            return
        p = plain.strip()
        if not p:
            setattr(row, enc_col, None)
        else:
            setattr(row, enc_col, encrypt_secret(p))

    apply_field("encrypted_openai_key", openai_api_key, clear_openai)
    apply_field("encrypted_anthropic_key", anthropic_api_key, clear_anthropic)
    apply_field("encrypted_gemini_key", gemini_api_key, clear_gemini)

    db.commit()
    db.refresh(row)
    return row
