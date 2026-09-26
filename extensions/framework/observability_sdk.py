from typing import Dict, Any


class ObservabilityExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def record_trace(self, trace: Dict[str, Any]) -> None:
        pass
