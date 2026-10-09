from product_polish.mcp_connectors import MCPConnector, MCPConnectors, MCPResource, MCPTool


def test_mcp_tool_to_dict():
    tool = MCPTool(name="search", description="Search web", parameters={"query": "str"})
    d = tool.to_dict()
    assert d["name"] == "search"
    assert d["parameters"]["query"] == "str"


def test_mcp_resource_to_dict():
    resource = MCPResource(uri="file://1", name="Doc", mime_type="text/plain", meta={"size": 10})
    d = resource.to_dict()
    assert d["uri"] == "file://1"
    assert d["mime_type"] == "text/plain"


def test_connector_register_and_get_tool():
    connector = MCPConnector(name="c1")
    tool = MCPTool(name="t1", description="d")
    connector.register_tool(tool)
    assert connector.get_tool("t1") is tool
    assert connector.get_tool("missing") is None


def test_connector_list_tools():
    connector = MCPConnector(name="c1")
    connector.register_tool(MCPTool(name="t1", description="d"))
    connector.register_tool(MCPTool(name="t2", description="d"))
    assert len(connector.list_tools()) == 2


def test_connector_register_and_get_resource():
    connector = MCPConnector(name="c1")
    resource = MCPResource(uri="u1", name="r1")
    connector.register_resource(resource)
    assert connector.get_resource("u1") is resource
    assert connector.get_resource("missing") is None


def test_connector_list_resources():
    connector = MCPConnector(name="c1")
    connector.register_resource(MCPResource(uri="u1", name="r1"))
    connector.register_resource(MCPResource(uri="u2", name="r2"))
    assert len(connector.list_resources()) == 2


def test_connector_to_dict():
    connector = MCPConnector(name="c1", endpoint="http://e")
    connector.register_tool(MCPTool(name="t1", description="d"))
    connector.register_resource(MCPResource(uri="u1", name="r1"))
    d = connector.to_dict()
    assert d["name"] == "c1"
    assert d["endpoint"] == "http://e"
    assert len(d["tools"]) == 1
    assert len(d["resources"]) == 1


def test_registry_register_and_get():
    registry = MCPConnectors()
    connector = MCPConnector(name="c1")
    registry.register(connector)
    assert registry.get("c1") is connector
    assert registry.get("missing") is None


def test_registry_list_connectors():
    registry = MCPConnectors()
    registry.register(MCPConnector(name="c1"))
    registry.register(MCPConnector(name="c2"))
    assert len(registry.list_connectors()) == 2


def test_registry_unregister():
    registry = MCPConnectors()
    registry.register(MCPConnector(name="c1"))
    assert registry.unregister("c1") is True
    assert registry.unregister("c1") is False
    assert registry.get("c1") is None
