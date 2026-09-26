from typing import Dict, Any, List


class DataEngineeringExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return []
