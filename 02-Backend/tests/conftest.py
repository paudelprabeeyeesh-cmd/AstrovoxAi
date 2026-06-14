"""
Astravox Backend Testing Infrastructure
Unit and integration tests for all backend components.
"""

import pytest
import sys
import os
from pathlib import Path

# Setup paths
BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

# Test configuration
@pytest.fixture
def app():
    """Create Flask test app."""
    from server.app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI runner."""
    return app.test_cli_runner()


# Session fixtures
@pytest.fixture
def session_data():
    """Sample session data."""
    return {
        'user_id': 'test-user-123',
        'username': 'testuser',
        'subscription': 'free'
    }


@pytest.fixture
def sample_message():
    """Sample message data."""
    return {
        'message': 'Hello, how are you?',
        'conversation_id': 'test-conv-123'
    }


# Database fixtures
@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing."""
    db_path = tmp_path / "test.db"
    os.environ['Astravox_DB_PATH'] = str(db_path)
    yield db_path


@pytest.fixture(scope="session")
def test_config():
    """Global test configuration."""
    return {
        'DEMO_MODE': True,
        'TESTING': True,
        'PRESERVE_CONTEXT_ON_EXCEPTION': False,
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
    }
