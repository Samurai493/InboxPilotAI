"""Unit tests for Gmail OAuth URL and state signing (no live Google / DB required)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services import gmail_oauth


@pytest.fixture
def mock_oauth_settings():
    m = MagicMock()
    m.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    m.GOOGLE_CLIENT_SECRET = "test-client-secret"
    m.GOOGLE_REDIRECT_URI = "http://localhost:8000/api/v1/gmail/oauth/callback"
    m.SECRET_KEY = "unit-test-secret-key-at-least-32-chars"
    return m


@patch.object(gmail_oauth, "settings")
def test_create_authorization_url_returns_google_host(mock_settings, mock_oauth_settings):
    mock_settings.GOOGLE_CLIENT_ID = mock_oauth_settings.GOOGLE_CLIENT_ID
    mock_settings.GOOGLE_CLIENT_SECRET = mock_oauth_settings.GOOGLE_CLIENT_SECRET
    mock_settings.GOOGLE_REDIRECT_URI = mock_oauth_settings.GOOGLE_REDIRECT_URI
    mock_settings.SECRET_KEY = mock_oauth_settings.SECRET_KEY

    uid = uuid.uuid4()
    url = gmail_oauth.create_authorization_url(uid)

    assert url.startswith("https://accounts.google.com/o/oauth2/auth")
    assert "client_id=" in url
    assert mock_oauth_settings.GOOGLE_CLIENT_ID.split(".")[0] in url
    assert "state=" in url


@patch.object(gmail_oauth, "settings")
def test_verify_oauth_state_roundtrip(mock_settings, mock_oauth_settings):
    mock_settings.SECRET_KEY = mock_oauth_settings.SECRET_KEY

    uid = uuid.uuid4()
    signed = gmail_oauth._sign_oauth_state(uid)
    assert gmail_oauth.verify_oauth_state(signed) == uid


@patch.object(gmail_oauth, "settings")
def test_create_authorization_url_requires_client_config(mock_settings):
    mock_settings.GOOGLE_CLIENT_ID = None
    mock_settings.GOOGLE_CLIENT_SECRET = None
    mock_settings.GOOGLE_REDIRECT_URI = "http://localhost/cb"
    mock_settings.SECRET_KEY = "x" * 40

    with pytest.raises(RuntimeError, match="GOOGLE_CLIENT_ID"):
        gmail_oauth.create_authorization_url(uuid.uuid4())
