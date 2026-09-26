from typing import Dict, Any, List


class EcosystemExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def discover(self, capability: str) -> List[Dict[str, Any]]:
        return []
