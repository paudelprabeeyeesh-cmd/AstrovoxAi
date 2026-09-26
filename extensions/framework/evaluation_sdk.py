from typing import Dict, Any, List


class EvaluationExtensionSDK:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def submit_evaluation(self, evaluation: Dict[str, Any]) -> None:
        pass
