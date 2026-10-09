import sys
import types
from enum import Enum
from unittest.mock import MagicMock

# Stub heavy app dependencies before importing sandbox modules
app_stub = types.ModuleType("app")
audit_stub = types.ModuleType("app.audit")
rbac_stub = types.ModuleType("app.rbac")
circuit_breaker_stub = types.ModuleType("app.circuit_breaker")
retry_stub = types.ModuleType("app.retry")
tool_executor_stub = types.ModuleType("app.tool_executor")


class FakePermission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


audit_stub.audit_logger = MagicMock()
rbac_stub.has_permission = lambda user_id, permission, resource: True
rbac_stub.Permission = FakePermission


class FakeCircuitBreaker:
    def __init__(self, *args, **kwargs):
        self.state = "closed"

    def call(self, func, *args, **kwargs):
        return func(*args, **kwargs)


circuit_breaker_stub.CircuitBreaker = FakeCircuitBreaker
cb_state = type("FakeState", (), {"OPEN": "open"})()
circuit_breaker_stub.CircuitState = cb_state
retry_stub.retry_with_backoff = lambda **kwargs: lambda f: f
tool_executor_stub.ToolExecutor = MagicMock

sys.modules["app"] = app_stub
sys.modules["app.audit"] = audit_stub
sys.modules["app.rbac"] = rbac_stub
sys.modules["app.circuit_breaker"] = circuit_breaker_stub
sys.modules["app.retry"] = retry_stub
sys.modules["app.tool_executor"] = tool_executor_stub

import pytest

from sandboxing.tool_sandbox import ToolSandbox, ToolSandboxStatus, TOOL_TIER_MAP
from sandboxing.approval_store import approval_store
from sandboxing.tool_metrics import tool_metrics


class FakeExecutor:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def execute_tool(self, tool_name: str, arguments: dict, user_id: str) -> str:
        self.calls.append((tool_name, arguments, user_id))
        if tool_name in self.responses:
            return self.responses[tool_name]
        return f"executed {tool_name}"


@pytest.fixture(autouse=True)
def reset_stores():
    approval_store._store.clear()
    approval_store._history.clear()
    tool_metrics._metrics.clear()
    yield
    approval_store._store.clear()
    approval_store._history.clear()
    tool_metrics._metrics.clear()


@pytest.fixture(autouse=True)
def reset_audit_logger():
    audit_stub.audit_logger = MagicMock()
    yield
    audit_stub.audit_logger = MagicMock()


def test_read_tool_auto_approved():
    executor = FakeExecutor(responses={"search_web": "result"})
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    result = sandbox.execute("search_web", {"query": "hello"}, "user-1")
    assert result.status == ToolSandboxStatus.APPROVED
    assert result.output == "result"
    m = tool_metrics.get("search_web")
    assert m is not None
    assert m.total_calls == 1
    assert m.success_count == 1


def test_write_tool_requires_approval():
    executor = FakeExecutor()
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    result = sandbox.execute("file_write", {"file_path": "/tmp/x", "content": "y"}, "user-1")
    assert result.status == ToolSandboxStatus.PENDING_APPROVAL
    assert result.approval_id is not None
    m = tool_metrics.get("file_write")
    assert m is not None
    assert m.pending_approvals == 1


def test_approve_and_execute_records_metrics():
    executor = FakeExecutor(responses={"file_write": "ok"})
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    pending = sandbox.execute("file_write", {"file_path": "/tmp/x", "content": "y"}, "user-1")
    assert pending.status == ToolSandboxStatus.PENDING_APPROVAL
    result = sandbox.approve(pending.approval_id, "user-1")
    assert result is not None
    assert result.status == ToolSandboxStatus.APPROVED
    assert result.output == "ok"
    m = tool_metrics.get("file_write")
    assert m.pending_approvals == 0
    assert m.total_calls >= 1


def test_reject_returns_denied_and_records_metrics():
    executor = FakeExecutor()
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    pending = sandbox.execute("file_write", {"file_path": "/tmp/x", "content": "y"}, "user-1")
    result = sandbox.reject(pending.approval_id, "user-1")
    assert result is not None
    assert result.status == ToolSandboxStatus.DENIED
    m = tool_metrics.get("file_write")
    assert m.pending_approvals == 0


def test_circuit_breaker_open_prevents_execution():
    executor = FakeExecutor()
    cb = MagicMock()
    cb.state = "open"
    cb.call.side_effect = Exception("open")
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0, tool_circuit_breaker=cb)
    result = sandbox.execute("search_web", {"query": "x"}, "user-1")
    assert result.status == ToolSandboxStatus.ERROR


def test_per_tool_circuit_breaker_open():
    executor = FakeExecutor()

    class PerToolCB:
        state = "open"

        def call(self, func, *args, **kwargs):
            raise Exception("per-tool open")

    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    sandbox._per_tool_breakers["search_web"] = PerToolCB()
    result = sandbox.execute("search_web", {"query": "x"}, "user-1")
    assert result.status == ToolSandboxStatus.ERROR
    m = tool_metrics.get("search_web")
    assert m.circuit_breaker_rejections >= 1


def test_audit_logging_on_execute():
    executor = FakeExecutor(responses={"search_web": "ok"})
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    sandbox.execute("search_web", {"query": "x"}, "user-1")
    assert audit_stub.audit_logger.log_tool_call.called


def test_audit_logging_on_pending_approval():
    executor = FakeExecutor()
    sandbox = ToolSandbox(tool_executor=executor, max_retries=0)
    result = sandbox.execute("file_write", {"file_path": "/tmp/x", "content": "y"}, "user-1")
    assert result.status == ToolSandboxStatus.PENDING_APPROVAL
    assert audit_stub.audit_logger.log.called
