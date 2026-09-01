"""Integration tests for chat, memory, and auth endpoints."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


# ============================================================================
# Health & Status Endpoint Tests
# ============================================================================

class TestHealthEndpoints:
    def test_health_check(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "astravox-ai-backend"

    def test_readiness_check(self):
        client = TestClient(app)
        response = client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self):
        client = TestClient(app)
        response = client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_root_endpoint(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "ASTRAVOX" in data["message"]
        assert data["status"] == "operational"

    def test_metrics_endpoint(self):
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code in [200, 500]


# ============================================================================
# API Status Tests
# ============================================================================

class TestAPIEndpoints:
    def test_api_status(self):
        client = TestClient(app)
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert data["service"] == "astravox-ai-api"


# ============================================================================
# Chat Models Endpoint Tests
# ============================================================================

class TestChatModelsEndpoint:
    def test_list_models(self):
        client = TestClient(app)
        response = client.get("/chat/models")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert len(data["models"]) >= 10

    def test_list_models_contains_openai(self):
        client = TestClient(app)
        response = client.get("/chat/models")
        data = response.json()
        providers = [m["provider"] for m in data["models"]]
        assert "openai" in providers

    def test_list_models_contains_anthropic(self):
        client = TestClient(app)
        response = client.get("/chat/models")
        data = response.json()
        providers = [m["provider"] for m in data["models"]]
        assert "anthropic" in providers

    def test_list_models_contains_gemini(self):
        client = TestClient(app)
        response = client.get("/chat/models")
        data = response.json()
        providers = [m["provider"] for m in data["models"]]
        assert "gemini" in providers

    def test_list_models_contains_ollama(self):
        client = TestClient(app)
        response = client.get("/chat/models")
        data = response.json()
        providers = [m["provider"] for m in data["models"]]
        assert "ollama" in providers


# ============================================================================
# Embedding Status Endpoint Tests
# ============================================================================

class TestEmbeddingEndpoints:
    def test_embedding_status(self):
        client = TestClient(app)
        response = client.get("/api/embedding/status")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "model" in data


# ============================================================================
# Auth Validation Tests
# ============================================================================

class TestAuthValidation:
    def test_signup_requires_email(self):
        client = TestClient(app)
        response = client.post("/auth/signup", json={
            "password": "test123",
            "full_name": "Test User",
        })
        assert response.status_code == 422

    def test_signup_requires_password(self):
        client = TestClient(app)
        response = client.post("/auth/signup", json={
            "email": "test@example.com",
            "full_name": "Test User",
        })
        assert response.status_code == 422

    def test_login_requires_email(self):
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "password": "test123",
        })
        assert response.status_code == 422

    def test_login_requires_password(self):
        client = TestClient(app)
        response = client.post("/auth/login", json={
            "email": "test@example.com",
        })
        assert response.status_code == 422

    def test_logout(self):
        client = TestClient(app)
        response = client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_me_requires_auth(self):
        client = TestClient(app)
        response = client.get("/auth/me")
        assert response.status_code == 401


# ============================================================================
# Chat Validation Tests
# ============================================================================

class TestChatValidation:
    def test_create_conversation_requires_auth(self):
        client = TestClient(app)
        response = client.post("/chat/conversations", json={
            "title": "Test",
            "model": "gpt-4",
        })
        assert response.status_code == 401

    def test_send_message_requires_auth(self):
        client = TestClient(app)
        response = client.post("/chat/message", json={
            "conversation_id": 1,
            "message": "Hello",
            "model": "gpt-4",
        })
        assert response.status_code == 401

    def test_list_conversations_requires_auth(self):
        client = TestClient(app)
        response = client.get("/chat/conversations")
        assert response.status_code == 401

    def test_invalid_model_rejected(self):
        client = TestClient(app)
        response = client.post("/chat/conversations", json={
            "title": "Test",
            "model": "invalid-model-xyz",
        }, headers={"Authorization": "Bearer fake-token"})
        assert response.status_code in [401, 422]


# ============================================================================
# Memory Validation Tests
# ============================================================================

class TestMemoryValidation:
    def test_save_memory_requires_auth(self):
        client = TestClient(app)
        response = client.post("/memory/save", json={
            "content": "Test memory",
            "importance": 1,
        })
        assert response.status_code == 401

    def test_get_memory_requires_auth(self):
        client = TestClient(app)
        response = client.get("/memory/")
        assert response.status_code == 401

    def test_memory_context_requires_auth(self):
        client = TestClient(app)
        response = client.post("/memory/context")
        assert response.status_code == 401


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    def test_404_for_unknown_route(self):
        client = TestClient(app)
        response = client.get("/nonexistent-route")
        assert response.status_code == 404

    def test_invalid_json_body(self):
        client = TestClient(app)
        response = client.post(
            "/auth/login",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
