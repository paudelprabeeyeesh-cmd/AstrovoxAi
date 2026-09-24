"""
Tests for product_polish.mcp_connectors

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.mcp_connectors import (  # noqa: E402
    MCPConnector,
    MCPConnectors,
    MCPResource,
    MCPTool,
)


@pytest.fixture()
def connector():
    return MCPConnector(name="test-conn", endpoint="http://example.com/mcp")


@pytest.fixture()
def registry():
    return MCPConnectors()


class TestMCPTool:
    def test_to_dict_contains_name(self):
        t = MCPTool(name="search", description="Search")
        d = t.to_dict()
        assert d["name"] == "search"

    def test_to_dict_contains_description(self):
        t = MCPTool(name="search", description="Search the web")
        d = t.to_dict()
        assert d["description"] == "Search the web"

    def test_to_dict_contains_parameters(self):
        t = MCPTool(name="search", description="", parameters={"query": "str"})
        d = t.to_dict()
        assert d["parameters"] == {"query": "str"}

    def test_default_parameters_empty(self):
        t = MCPTool(name="search", description="")
        assert t.parameters == {}


class TestMCPResource:
    def test_to_dict_contains_uri(self):
        r = MCPResource(uri="file:///x", name="res")
        d = r.to_dict()
        assert d["uri"] == "file:///x"

    def test_to_dict_contains_name(self):
        r = MCPResource(uri="file:///x", name="res")
        d = r.to_dict()
        assert d["name"] == "res"

    def test_default_mime_type_empty(self):
        r = MCPResource(uri="file:///x", name="res")
        assert r.mime_type == ""

    def test_custom_mime_type(self):
        r = MCPResource(uri="file:///x", name="res", mime_type="text/plain")
        assert r.mime_type == "text/plain"

    def test_to_dict_contains_meta(self):
        r = MCPResource(uri="file:///x", name="res", meta={"key": "v"})
        d = r.to_dict()
        assert d["meta"] == {"key": "v"}


class TestMCPConnectorInit:
    def test_name_set(self, connector):
        assert connector.name == "test-conn"

    def test_endpoint_set(self, connector):
        assert connector.endpoint == "http://example.com/mcp"

    def test_initial_tools_empty(self, connector):
        assert connector.list_tools() == []

    def test_initial_resources_empty(self, connector):
        assert connector.list_resources() == []


class TestMCPConnectorRegisterTool:
    def test_register_adds_tool(self, connector):
        t = MCPTool(name="search", description="Search")
        connector.register_tool(t)
        assert len(connector.list_tools()) == 1

    def test_get_tool_existing(self, connector):
        t = MCPTool(name="search", description="Search")
        connector.register_tool(t)
        got = connector.get_tool("search")
        assert got is not None
        assert got.name == "search"

    def test_get_tool_missing_returns_none(self, connector):
        assert connector.get_tool("missing") is None

    def test_register_overwrites_existing(self, connector):
        t1 = MCPTool(name="search", description="v1")
        t2 = MCPTool(name="search", description="v2")
        connector.register_tool(t1)
        connector.register_tool(t2)
        assert connector.get_tool("search").description == "v2"

    def test_register_multiple_tools(self, connector):
        connector.register_tool(MCPTool(name="a", description=""))
        connector.register_tool(MCPTool(name="b", description=""))
        assert len(connector.list_tools()) == 2

    def test_list_tools_returns_all(self, connector):
        connector.register_tool(MCPTool(name="a", description=""))
        connector.register_tool(MCPTool(name="b", description=""))
        names = [t.name for t in connector.list_tools()]
        assert "a" in names
        assert "b" in names


class TestMCPConnectorRegisterResource:
    def test_register_adds_resource(self, connector):
        r = MCPResource(uri="file:///x", name="res")
        connector.register_resource(r)
        assert len(connector.list_resources()) == 1

    def test_get_resource_existing(self, connector):
        r = MCPResource(uri="file:///x", name="res")
        connector.register_resource(r)
        got = connector.get_resource("file:///x")
        assert got is not None
        assert got.name == "res"

    def test_get_resource_missing_returns_none(self, connector):
        assert connector.get_resource("file:///missing") is None

    def test_register_multiple_resources(self, connector):
        connector.register_resource(MCPResource(uri="file:///x", name="r1"))
        connector.register_resource(MCPResource(uri="file:///y", name="r2"))
        assert len(connector.list_resources()) == 2


class TestMCPConnectorToDict:
    def test_to_dict_contains_name(self, connector):
        d = connector.to_dict()
        assert d["name"] == "test-conn"

    def test_to_dict_contains_endpoint(self, connector):
        d = connector.to_dict()
        assert d["endpoint"] == "http://example.com/mcp"

    def test_to_dict_contains_tools_list(self, connector):
        connector.register_tool(MCPTool(name="t", description=""))
        d = connector.to_dict()
        assert isinstance(d["tools"], list)
        assert len(d["tools"]) == 1

    def test_to_dict_contains_resources_list(self, connector):
        connector.register_resource(MCPResource(uri="file:///x", name="r"))
        d = connector.to_dict()
        assert isinstance(d["resources"], list)
        assert len(d["resources"]) == 1


class TestMCPConnectorsRegistry:
    def test_register_and_get(self, registry):
        c = MCPConnector(name="c1", endpoint="http://e")
        registry.register(c)
        assert registry.get("c1") is c

    def test_get_missing_returns_none(self, registry):
        assert registry.get("missing") is None

    def test_list_empty_initially(self, registry):
        assert registry.list_connectors() == []

    def test_unregister_returns_true(self, registry):
        c = MCPConnector(name="c1", endpoint="")
        registry.register(c)
        assert registry.unregister("c1") is True

    def test_unregister_removes(self, registry):
        c = MCPConnector(name="c1", endpoint="")
        registry.register(c)
        registry.unregister("c1")
        assert registry.get("c1") is None

    def test_unregister_missing_returns_False(self, registry):
        assert registry.unregister("missing") is False

    def test_register_multiple(self, registry):
        registry.register(MCPConnector(name="a", endpoint=""))
        registry.register(MCPConnector(name="b", endpoint=""))
        assert len(registry.list_connectors()) == 2

    def test_register_overwrites(self, registry):
        c1 = MCPConnector(name="c1", endpoint="http://old")
        c2 = MCPConnector(name="c1", endpoint="http://new")
        registry.register(c1)
        registry.register(c2)
        assert registry.get("c1") is c2


class TestMCPConnectorsThreadSafety:
    def test_concurrent_registers(self, registry):
        import threading
        errors = []

        def register_many():
            try:
                for i in range(20):
                    registry.register(MCPConnector(name=f"c{i}", endpoint=""))
            except Exception as _e:  # noqa: BLE001
                errors.append(_e)

        threads = [threading.Thread(target=register_many) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
