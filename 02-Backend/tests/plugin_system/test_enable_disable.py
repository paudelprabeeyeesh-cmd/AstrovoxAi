from plugin_system import PluginManager


class TestEnableDisable:
    def test_enable_existing_plugin(self):
        manager = PluginManager()

        def plugin_func():
            pass

        manager.register("plugin1", plugin_func, enabled=False)
        assert manager.is_enabled("plugin1") is False
        manager.enable("plugin1")
        assert manager.is_enabled("plugin1") is True

    def test_disable_existing_plugin(self):
        manager = PluginManager()

        def plugin_func():
            pass

        manager.register("plugin2", plugin_func)
        assert manager.is_enabled("plugin2") is True
        manager.disable("plugin2")
        assert manager.is_enabled("plugin2") is False

    def test_enable_nonexistent_plugin(self):
        manager = PluginManager()
        manager.enable("ghost")
        assert "ghost" not in manager.list_plugins()

    def test_disable_nonexistent_plugin(self):
        manager = PluginManager()
        manager.disable("ghost")
        assert "ghost" not in manager.list_plugins()

    def test_toggle_affects_hook_execution(self):
        manager = PluginManager()

        def plugin_a():
            return "a"

        def plugin_b():
            return "b"

        manager.register("a", plugin_a, hooks=["on_call"], enabled=False)
        manager.register("b", plugin_b, hooks=["on_call"], enabled=True)
        results = manager.execute_hook("on_call")
        assert results == ["b"]
        manager.enable("a")
        results = manager.execute_hook("on_call")
        assert "a" in results
        assert "b" in results
