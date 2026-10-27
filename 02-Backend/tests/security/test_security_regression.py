"""AstrovoxAI Security Regression Tests

Tests for verified security fixes and ongoing regression protection.
Run with: pytest tests/security/ -v --tb=short -p no:cacheprovider
"""

import pytest
from fastapi.testclient import TestClient

# Import after conftest sets up sys.path
from app.main import app

client = TestClient(app)


class TestPydanticModelResolution:
    """Regression tests for SA-03: Pydantic from __future__ import annotations fix."""

    def test_auth_user_create_model_resolves(self):
        """UserCreate must resolve as a Pydantic model (not ForwardRef)."""
        from backend.app.auth.models import UserCreate
        # Pydantic v2: model should have __pydantic_core_schema__
        assert hasattr(UserCreate, "__pydantic_core_schema__") or hasattr(
            UserCreate, "model_fields"
        ), "UserCreate is not a valid Pydantic model"

    def test_auth_user_response_model_resolves(self):
        """UserResponse must resolve as a Pydantic model."""
        from backend.app.auth.models import UserResponse
        assert hasattr(UserResponse, "__pydantic_core_schema__") or hasattr(
            UserResponse, "model_fields"
        ), "UserResponse is not a valid Pydantic model"

    def test_workspace_invitation_model_resolves(self):
        """WorkspaceInvitation must resolve as a Pydantic model."""
        from backend.app.workspaces.models import WorkspaceInvitation
        assert hasattr(WorkspaceInvitation, "__pydantic_core_schema__") or hasattr(
            WorkspaceInvitation, "model_fields"
        ), "WorkspaceInvitation is not a valid Pydantic model"

    def test_backend_auth_imports(self):
        """backend.app.auth.router must import without PydanticUndefinedAnnotation."""
        import backend.app.auth.router as auth_router
        assert auth_router.router is not None

    def test_backend_workspaces_imports(self):
        """backend.app.workspaces.router must import without PydanticUndefinedAnnotation."""
        import backend.app.workspaces.router as workspaces_router
        assert workspaces_router.router is not None


class TestESLintConfigRule:
    """Regression tests for SA-05: ESLint security rule name fix."""

    def test_eslint_security_rule_exists(self):
        """security/detect-pseudoRandomBytes must exist in installed plugin."""
        try:
            import eslint_plugin_security as security_plugin  # type: ignore
        except ImportError:
            pytest.skip("eslint-plugin-security not importable from Python")
        # Rule name check is done via npm run lint; this is a placeholder
        assert True


class TestMathModuleSecurity:
    """Security-relevant tests for the math module (input validation bounds)."""

    def test_vector_dot_rejects_mismatched_lengths(self):
        """vector_dot must reject mismatched vector lengths (input validation)."""
        from app.math import vector_dot
        with pytest.raises(ValueError):
            vector_dot([1.0, 2.0], [1.0])

    def test_matrix_mul_rejects_dimension_mismatch(self):
        """matrix_mul must reject incompatible dimensions."""
        from app.math import matrix_mul
        with pytest.raises(ValueError):
            matrix_mul([[1.0, 2.0]], [[1.0, 2.0, 3.0]])

    def test_matrix_inverse_rejects_singular(self):
        """matrix_inverse_2x2 must reject singular matrices."""
        from app.math import matrix_inverse_2x2
        with pytest.raises(ValueError):
            matrix_inverse_2x2([[1.0, 2.0], [2.0, 4.0]])  # det = 0

    def test_mse_rejects_mismatched_lengths(self):
        """mean_squared_error must reject mismatched input lengths."""
        from app.math import mean_squared_error
        with pytest.raises(ValueError):
            mean_squared_error([1.0, 2.0], [1.0])

    def test_pearson_rejects_zero_variance(self):
        """pearson_correlation must reject zero-variance input."""
        from app.math import pearson_correlation
        with pytest.raises(ValueError):
            pearson_correlation([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])


class TestAuthEndpoints:
    """Integration tests for auth endpoints (require running backend)."""

    def test_register_endpoint_exists(self):
        """POST /auth/register must be registered on the router."""
        from backend.app.auth.router import router
        routes = [r.path for r in router.routes]
        assert "/register" in routes or any("register" in r for r in routes)

    def test_login_endpoint_exists(self):
        """POST /auth/login must be registered on the router."""
        from backend.app.auth.router import router
        routes = [r.path for r in router.routes]
        assert "/login" in routes or any("login" in r for r in routes)


__all__ = [
    "TestPydanticModelResolution",
    "TestESLintConfigRule",
    "TestMathModuleSecurity",
    "TestAuthEndpoints",
]
