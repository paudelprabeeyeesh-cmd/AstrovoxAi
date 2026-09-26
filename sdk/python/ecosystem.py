from typing import Dict, Any, List


class EcosystemClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_plugins(self, capability: str) -> List[Dict[str, Any]]:
        return []

    def install_plugin(self, plugin_id: str) -> None:
        pass
