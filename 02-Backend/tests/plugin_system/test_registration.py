from plugin_system import PluginManager


class TestRegistration:
    def test_register_function(self):
        manager = PluginManager()

        def my_plugin():
            pass

        manager.register("my_plugin", my_plugin, hooks=["on_start"])
        assert "my_plugin" in manager.list_plugins()

    def test_register_with_decorator(self):
        manager = PluginManager()

        @manager.register("decorated", hooks=["on_event"])
        def decorated_plugin():
            pass

        assert "decorated" in manager.list_plugins()
        assert decorated_plugin() is None

    def test_register_default_enabled(self):
        manager = PluginManager()

        def plugin_func():
            pass

        manager.register("auto_enabled", plugin_func)
        assert manager.is_enabled("auto_enabled") is True

    def test_register_disabled(self):
        manager = PluginManager()

        def plugin_func():
            pass

        manager.register("disabled_plugin", plugin_func, enabled=False)
        assert manager.is_enabled("disabled_plugin") is False

    def test_register_duplicate_name(self):
        manager = PluginManager()

        def plugin_v1():
            return "v1"

        def plugin_v2():
            return "v2"

        manager.register("same", plugin_v1)
        manager.register("same", plugin_v2)
        assert manager.get_plugin("same")["func"]() == "v2"
