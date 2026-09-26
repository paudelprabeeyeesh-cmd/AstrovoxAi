from typing import Dict, Any


class MLOpsExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def log_params(self, experiment_id: str, params: Dict[str, Any]) -> None:
        pass

    def log_metrics(self, experiment_id: str, metrics: Dict[str, float]) -> None:
        pass
