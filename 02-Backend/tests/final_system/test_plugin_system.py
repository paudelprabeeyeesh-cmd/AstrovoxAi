from final_system.plugin_system import Plugin, PluginManager, PluginStatus


def test_register_and_get():
    pm = PluginManager()
    plugin = Plugin(name="core", version="1.0.0")
    pm.register(plugin)
    assert pm.get("core") is plugin


def test_unregister():
    pm = PluginManager()
    plugin = Plugin(name="core")
    pm.register(plugin)
    pm.unregister("core")
    assert pm.get("core") is None


def test_activate_disable():
    pm = PluginManager()
    plugin = Plugin(name="core")
    pm.register(plugin)
    pm.activate("core")
    assert pm.get("core").status == PluginStatus.ACTIVE
    pm.disable("core")
    assert pm.get("core").status == PluginStatus.DISABLED


def test_hook():
    pm = PluginManager()
    results = []
    plugin = Plugin(name="core", hooks={"on_event": [lambda x: results.append(x)]})
    pm.register(plugin)
    pm.hook("on_event", 42)
    assert results == [42]


def test_list_plugins():
    pm = PluginManager()
    pm.register(Plugin(name="a"))
    pm.register(Plugin(name="b"))
    assert set(pm.list_plugins()) == {"a", "b"}
