"""
Unit tests for utilities module.
Tests logging, validation, and middleware functions.
"""

import pytest
import sys
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from utils.validators import (
    validate_email,
    validate_username,
    validate_password,
    sanitize_string,
    sanitize_integer,
    ValidationError,
)


class TestValidators:
    """Test validation utilities."""
    
    def test_validate_email_valid(self):
        """Test valid email."""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@subdomain.co.uk") is True
    
    def test_validate_email_invalid(self):
        """Test invalid email."""
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False
    
    def test_validate_username_valid(self):
        """Test valid username."""
        assert validate_username("user123") is True
        assert validate_username("test_user") is True
        assert validate_username("abc") is True
    
    def test_validate_username_invalid(self):
        """Test invalid username."""
        assert validate_username("ab") is False  # Too short
        assert validate_username("user-name") is False  # Hyphen not allowed
        assert validate_username("user@name") is False  # Special char
        assert validate_username("") is False
        assert validate_username("x" * 21) is False  # Too long
    
    def test_validate_password_valid(self):
        """Test valid password."""
        assert validate_password("password123") is True
        assert validate_password("secure_p@ssw0rd") is True
    
    def test_validate_password_invalid(self):
        """Test invalid password."""
        assert validate_password("short") is False
        assert validate_password("") is False
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        assert sanitize_string("  hello  ") == "hello"
        assert sanitize_string("test\x00value") == "testvalue"
        assert sanitize_string("x" * 2000, max_length=100) == "x" * 100
    
    def test_sanitize_integer_valid(self):
        """Test integer sanitization."""
        assert sanitize_integer(42) == 42
        assert sanitize_integer("100") == 100
        assert sanitize_integer(50, min_val=10, max_val=100) == 50
    
    def test_sanitize_integer_bounds(self):
        """Test integer bounds validation."""
        with pytest.raises(ValidationError):
            sanitize_integer(5, min_val=10)
        
        with pytest.raises(ValidationError):
            sanitize_integer(150, max_val=100)
    
    def test_sanitize_integer_invalid(self):
        """Test invalid integer."""
        with pytest.raises(ValidationError):
            sanitize_integer("not a number")


class TestDecorators:
    """Test validation decorators."""
    
    def test_require_json(self, client):
        """Test JSON requirement decorator."""
        response = client.post(
            '/chat/message',
            data='not json',
            content_type='text/plain'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'ERROR'
    
    def test_require_fields(self, client):
        """Test required fields decorator."""
        response = client.post(
            '/chat/message',
            json={'message': 'hello'},  # Missing conversation_id
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'missing' in data or 'MISSING_FIELDS' in data.get('code', '')


class TestLogging:
    """Test logging setup."""
    
    def test_logger_setup(self):
        """Test logger is properly configured."""
        from utils.logger import app_logger, chat_logger, ai_logger
        
        assert app_logger is not None
        assert chat_logger is not None
        assert ai_logger is not None
        assert len(app_logger.handlers) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
