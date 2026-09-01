"""Pytest configuration for the canonical FastAPI backend.

Sets dummy Supabase credentials before the app is imported so the shared
client can be constructed without real secrets, and exposes the backend
package on sys.path.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Backend root (02-Backend) so `import app.main` resolves.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Dummy creds: the health/readiness/root routes never call Supabase, but the
# shared client is created at import time and requires these to be set.
os.environ.setdefault("VITE_SUPABASE_URL", "https://dummy.supabase.co")
os.environ.setdefault("VITE_SUPABASE_ANON_KEY", "dummy-anon-key")


@pytest.fixture(autouse=True)
def mock_supabase_auth():
    """Mock Supabase auth for all tests."""
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.email = "test@example.com"

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_auth = MagicMock()
    mock_auth.get_user.return_value = mock_response

    mock_client = MagicMock()
    mock_client.auth = mock_auth

    with patch("app.auth_utils.get_supabase", return_value=mock_client):
        with patch("app.supabase_client.get_supabase", return_value=mock_client):
            yield
