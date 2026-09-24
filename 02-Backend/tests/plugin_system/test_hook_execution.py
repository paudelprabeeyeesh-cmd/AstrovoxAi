from plugin_system import PluginManager


class TestHookExecution:
    def test_hook_with_no_plugins(self):
        manager = PluginManager()
        results = manager.execute_hook("missing")
        assert results == []

    def test_hook_with_single_plugin(self):
        manager = PluginManager()

        def plugin_a(x):
            return x + 1

        manager.register("a", plugin_a, hooks=["transform"])
        results = manager.execute_hook("transform", 1)
        assert results == [2]

    def test_hook_with_multiple_plugins(self):
        manager = PluginManager()

        def plugin_a(x):
            return x + 1

        def plugin_b(x):
            return x * 2

        manager.register("a", plugin_a, hooks=["transform"])
        manager.register("b", plugin_b, hooks=["transform"])
        results = manager.execute_hook("transform", 3)
        assert 4 in results
        assert 6 in results

    def test_hook_skips_disabled_plugins(self):
        manager = PluginManager()

        def plugin_a(x):
            return x + 1

        def plugin_b(x):
            return x * 2

        manager.register("a", plugin_a, hooks=["transform"], enabled=False)
        manager.register("b", plugin_b, hooks=["transform"], enabled=True)
        results = manager.execute_hook("transform", 3)
        assert results == [6]

    def test_hook_with_kwargs(self):
        manager = PluginManager()

        def plugin_a(value, offset=0):
            return value + offset

        manager.register("a", plugin_a, hooks=["adjust"])
        results = manager.execute_hook("adjust", 10, offset=5)
        assert results == [15]

    def test_hook_continues_on_exception(self):
        manager = PluginManager()

        def good_plugin(x):
            return x

        def bad_plugin(x):
            raise RuntimeError("fail")

        manager.register("good", good_plugin, hooks=["resilient"])
        manager.register("bad", bad_plugin, hooks=["resilient"])
        results = manager.execute_hook("resilient", 1)
        assert results == [1]
