"""Security integration tests for AstrovoxAI backend."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.core.tracing import init_tracing, OPENTELEMETRY_AVAILABLE
from app.secret_rotation import SecretRotationService, SecretBackend


class TestDistributedTracing(unittest.TestCase):
    """Ensure tracing can be initialized."""

    def test_tracing_initialization(self):
        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": ""}):
            tracer = init_tracing(service_name="test-service", app=app)
            if tracer is not None:
                self.assertTrue(OPENTELEMETRY_AVAILABLE)


class TestSecretRotation(unittest.TestCase):
    """Ensure secret rotation service works."""

    def test_rotate_environment_secret(self):
        service = SecretRotationService(backend=SecretBackend.ENVIRONMENT)
        secret_name = "TEST_SECRET_ROTATION"
        if secret_name in os.environ:
            del os.environ[secret_name]

        new_value = service.rotate_secret(secret_name)
        self.assertEqual(os.environ.get(secret_name), new_value)
        self.assertTrue(service.verify_rotation(secret_name))

        del os.environ[secret_name]

    def test_schedule_rotation(self):
        service = SecretRotationService()
        service.schedule_rotation("MY_SECRET", interval_days=30)
        due = service.check_due_rotations()
        self.assertEqual(due, [])


if __name__ == "__main__":
    unittest.main()
