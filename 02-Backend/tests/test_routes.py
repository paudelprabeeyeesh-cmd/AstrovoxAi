"""
Integration tests for API routes.
Tests chat, auth, and other endpoints.
"""

import pytest
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


class TestChatRoutes:
    """Test chat-related endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/chat/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'OK'
        assert 'ai_available' in data
    
    def test_message_missing_fields(self, client):
        """Test message endpoint with missing fields."""
        response = client.post(
            '/chat/message',
            json={'message': 'hello'},  # Missing conversation_id
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'ERROR'
    
    def test_message_empty_text(self, client):
        """Test message endpoint with empty text."""
        response = client.post(
            '/chat/message',
            json={
                'message': '',
                'conversation_id': 'test-conv'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_history_endpoint(self, client):
        """Test history retrieval endpoint."""
        response = client.get('/chat/history/nonexistent-conv')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'OK'
        assert data['history'] == []


class TestAuthRoutes:
    """Test authentication endpoints."""
    
    def test_auth_status_no_session(self, client):
        """Test auth status when not logged in."""
        response = client.get('/auth/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['authenticated'] is False


class TestAPIRoutes:
    """Test API endpoints."""
    
    def test_api_health(self, client):
        """Test API health endpoint."""
        response = client.get('/api/health')
        # May return 404 if not implemented
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = client.put('/chat/message')
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
