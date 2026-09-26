from typing import Dict, Any, List


class EnterpriseSuiteExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_gateways(self) -> List[Dict[str, Any]]:
        return []
