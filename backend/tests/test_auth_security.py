"""Tests for guest JWT and require_user_context."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import auth_service


@patch.object(auth_service, "settings")
def test_guest_token_roundtrip(mock_st):
    mock_st.SECRET_KEY = "unit-test-secret-key-at-least-32-chars!!"
    mock_st.ALGORITHM = "HS256"
    mock_st.GUEST_TOKEN_EXPIRE_DAYS = 7

    uid = uuid.uuid4()
    token = auth_service.create_guest_access_token(uid)
    assert isinstance(token, str)
    assert len(token) > 20


def test_require_user_context_mismatch():
    user = MagicMock()
    user.id = uuid.uuid4()
    other = str(uuid.uuid4())
    with pytest.raises(HTTPException) as ei:
        auth_service.require_user_context(user, other)
    assert ei.value.status_code == 403


def test_require_user_context_ok():
    uid = uuid.uuid4()
    user = MagicMock()
    user.id = uid
    assert auth_service.require_user_context(user, str(uid)) == str(uid)
    assert auth_service.require_user_context(user, None) == str(uid)
