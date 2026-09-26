from typing import Dict, Any, List


class ResearchLabExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_experiments(self) -> List[Dict[str, Any]]:
        return []
