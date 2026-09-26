from typing import Dict, Any


class StorageExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def save_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        pass
