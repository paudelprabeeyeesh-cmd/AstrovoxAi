from typing import Dict, Any


class ProductionExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def deploy(self, service: str, image: str) -> Dict[str, Any]:
        return {"status": "deployed"}
