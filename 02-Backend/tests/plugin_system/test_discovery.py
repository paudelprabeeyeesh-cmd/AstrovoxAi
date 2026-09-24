import os
import tempfile

from plugin_system import PluginManager


class TestDiscovery:
    def test_discover_empty_directory(self):
        manager = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            discovered = manager.discover(tmpdir)
        assert discovered == []

    def test_discover_single_plugin(self):
        manager = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_file = os.path.join(tmpdir, "sample_plugin.py")
            with open(plugin_file, "w", encoding="utf-8") as f:
                f.write(
                    "def register(mgr):\n"
                    "    mgr.register('sample', lambda: 'sample', hooks=['on_sample'])\n"
                )
            discovered = manager.discover(tmpdir)
        assert len(discovered) == 1
        assert "plugin_system.discovered.sample_plugin" in discovered
        assert "sample" in manager.list_plugins()

    def test_discover_skips_init(self):
        manager = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            with open(os.path.join(tmpdir, "plugin_a.py"), "w", encoding="utf-8") as f:
                f.write("def register(mgr):\n    mgr.register('a', lambda: 'a')\n")
            discovered = manager.discover(tmpdir)
        assert discovered == ["plugin_system.discovered.plugin_a"]

    def test_discover_ignores_non_py(self):
        manager = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "readme.txt"), "w", encoding="utf-8") as f:
                f.write("not a plugin")
            with open(os.path.join(tmpdir, "plugin.py"), "w", encoding="utf-8") as f:
                f.write("def register(mgr):\n    mgr.register('p', lambda: 'p')\n")
            discovered = manager.discover(tmpdir)
        assert discovered == ["plugin_system.discovered.plugin"]

    def test_discover_handles_bad_module(self):
        manager = PluginManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "bad.py"), "w", encoding="utf-8") as f:
                f.write("raise ValueError('oops')\n")
            discovered = manager.discover(tmpdir)
        assert discovered == []
