class PluginMarketplace:
    def __init__(self):
        self.plugins = {}

    def register(self, plugin_id, plugin):
        self.plugins[plugin_id] = plugin

    def install(self, plugin_id):
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin {plugin_id} not found")
        return self.plugins[plugin_id].install()

    def list_available(self):
        return list(self.plugins.keys())
