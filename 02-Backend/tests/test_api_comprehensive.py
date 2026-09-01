"""Comprehensive API integration tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ============================================================================
# Health & Status Tests
# ============================================================================

class TestHealthEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness(self):
        response = client.get("/health/readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_liveness(self):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "ASTRAVOX" in response.json()["message"]

    def test_metrics_endpoint(self):
        response = client.get("/metrics")
        assert response.status_code in [200, 500]


# ============================================================================
# Models Endpoint Tests
# ============================================================================

class TestModelsEndpoints:
    def test_list_models(self):
        response = client.get("/chat/models")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        assert len(data["models"]) >= 10

    def test_models_have_required_fields(self):
        response = client.get("/chat/models")
        data = response.json()
        for model in data["models"]:
            assert "id" in model
            assert "provider" in model
            assert "display_name" in model

    def test_models_contain_all_providers(self):
        response = client.get("/chat/models")
        data = response.json()
        providers = {m["provider"] for m in data["models"]}
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers
        assert "ollama" in providers


# ============================================================================
# Embedding Endpoint Tests
# ============================================================================

class TestEmbeddingEndpoints:
    def test_embedding_status(self):
        response = client.get("/api/embedding/status")
        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "model" in data


# ============================================================================
# Security Scan Tests
# ============================================================================

class TestSecurityScans:
    def test_pii_scan_clean(self):
        response = client.post(
            "/security-scan/pii",
            json={"text": "Hello world, this is a test."},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is True

    def test_pii_scan_detects_email(self):
        response = client.post(
            "/security-scan/pii",
            json={"text": "Contact me at test@example.com for details."},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is False
        assert len(data["issues"]) > 0

    def test_secret_scan_clean(self):
        response = client.post(
            "/security-scan/secrets",
            json={"text": "This is a normal message without secrets."},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is True

    def test_secret_scan_detects_key(self):
        response = client.post(
            "/security-scan/secrets",
            json={"text": "My API key is sk-abc123def456ghi789jkl012mno345pqr"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["safe"] is False


# ============================================================================
# Tools Endpoint Tests
# ============================================================================

class TestToolsEndpoints:
    def test_list_tools(self):
        response = client.get(
            "/tools/",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 5

    def test_tools_have_required_fields(self):
        response = client.get(
            "/tools/",
            headers={"Authorization": "Bearer test-token"},
        )
        data = response.json()
        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool

    def test_execute_calculator(self):
        response = client.post(
            "/tools/execute",
            json={"tool_name": "calculator", "parameters": {"expression": "2 + 2"}},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is not None


# ============================================================================
# Monitoring Endpoint Tests
# ============================================================================

class TestMonitoringEndpoints:
    def test_detailed_health(self):
        response = client.get("/monitoring/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]

    def test_uptime(self):
        response = client.get("/monitoring/uptime")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data

    def test_performance(self):
        response = client.get(
            "/monitoring/performance",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "system" in data

    def test_dashboard(self):
        response = client.get(
            "/monitoring/dashboard",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "system" in data


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    def test_404_for_unknown_route(self):
        response = client.get("/nonexistent-route-xyz")
        assert response.status_code == 404

    def test_invalid_json_body(self):
        response = client.post(
            "/tools/execute",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_method_not_allowed(self):
        response = client.delete("/health")
        assert response.status_code == 405
