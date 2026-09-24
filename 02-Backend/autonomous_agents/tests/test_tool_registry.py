from ..tool_registry import ToolRegistry


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register("search", "search docs")
        spec = reg.get("search")
        assert spec is not None
        assert spec.name == "search"

    def test_call_without_handler_returns_mock(self):
        reg = ToolRegistry()
        reg.register("ping", "ping tool")
        result = reg.call("ping")
        assert result == "mock:ping"

    def test_call_with_handler(self):
        reg = ToolRegistry()
        reg.register("add", "add two numbers", parameters={"a": 1, "b": 1}, handler=lambda a, b: a + b)
        assert reg.call("add", a=1, b=2) == 3

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register("x", "x")
        assert reg.unregister("x") is True
        assert reg.get("x") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register("a", "a")
        reg.register("b", "b")
        names = [t.name for t in reg.list_tools()]
        assert "a" in names
        assert "b" in names

    def test_call_missing_raises(self):
        reg = ToolRegistry()
        try:
            reg.call("missing")
        except KeyError:
            pass
        else:
            raise AssertionError("Expected KeyError")
