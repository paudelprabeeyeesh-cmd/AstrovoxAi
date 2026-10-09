import time
from unittest.mock import MagicMock

import pytest

from app.tool_registry import ToolRegistry, tool_registry, ToolHealthStatus


@pytest.fixture(autouse=True)
def reset_tool_registry():
    tool_registry._tools.clear()
    tool_registry._tags.clear()
    yield
    tool_registry._tools.clear()
    tool_registry._tags.clear()


def test_register_with_metadata_creates_tool_spec():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="admin_tool",
        description="admin only",
        handler=lambda: "ok",
        required_permissions=["admin"],
    )
    assert reg.check_permission("admin_tool", ["admin"]) is True
    assert reg.check_permission("admin_tool", ["user"]) is False


def test_register_backward_compatible():
    reg = ToolRegistry()

    class FakeTool:
        name = "legacy"
        description = "legacy tool"
        tags = []
        parameters = {}
        required_permissions = []
        version = "1.0.0"
        deprecated = False

    reg.register(FakeTool())
    assert reg.get("legacy") is not None


def test_list_all_includes_metadata():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="tool_a",
        description="desc",
        handler=lambda: "ok",
        required_permissions=["read"],
        version="2.0.0",
    )
    tools = reg.list_all()
    assert any(t["name"] == "tool_a" for t in tools)
    assert any(t["required_permissions"] == ["read"] for t in tools)


def test_search_ranks_by_relevance():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="search_web",
        description="Search the web",
        handler=lambda: "ok",
        tags=["search"],
    )
    results = reg.search("search")
    assert len(results) >= 1
    assert results[0]["name"] == "search_web"


def test_check_permission_missing_tool():
    reg = ToolRegistry()
    assert reg.check_permission("missing", ["admin"]) is False


def test_list_by_tag():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="search_web",
        description="Search",
        handler=lambda: "ok",
        tags=["search", "read"],
    )
    reg.register_with_metadata(
        name="search_docs",
        description="Docs",
        handler=lambda: "ok",
        tags=["search", "write"],
    )
    results = reg.list_by_tag("search")
    assert len(results) == 2


def test_deregister():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="temp_tool",
        description="temp",
        handler=lambda: "ok",
        tags=["temp"],
    )
    assert reg.get("temp_tool") is not None
    assert reg.deregister("temp_tool") is True
    assert reg.get("temp_tool") is None
    assert "temp" not in reg._tags


def test_get_metrics_summary():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="tool_a",
        description="a",
        handler=lambda: "ok",
        tags=["a"],
    )
    reg.register_with_metadata(
        name="tool_b",
        description="b",
        handler=lambda: "ok",
        tags=["b"],
        deprecated=True,
    )
    summary = reg.get_metrics_summary()
    assert summary["total_tools"] == 2
    assert summary["deprecated_tools"] == 1
    assert "a" in summary["tags"]
    assert "b" in summary["tags"]


def test_update_health():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="tool_a",
        description="a",
        handler=lambda: "ok",
    )
    reg.update_health("tool_a", ToolHealthStatus.HEALTHY)
    tool = reg.get("tool_a")
    assert tool.health_status == ToolHealthStatus.HEALTHY
    assert tool.last_health_check is not None


def test_get_unhealthy_tools():
    reg = ToolRegistry()
    reg.register_with_metadata(
        name="healthy_tool",
        description="a",
        handler=lambda: "ok",
    )
    reg.register_with_metadata(
        name="unhealthy_tool",
        description="b",
        handler=lambda: "ok",
    )
    reg.update_health("healthy_tool", ToolHealthStatus.HEALTHY)
    reg.update_health("unhealthy_tool", ToolHealthStatus.UNHEALTHY)
    unhealthy = reg.get_unhealthy_tools()
    assert len(unhealthy) == 1
    assert unhealthy[0].name == "unhealthy_tool"
