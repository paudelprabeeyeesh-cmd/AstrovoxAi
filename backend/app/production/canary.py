from typing import Dict


class CanaryDeployment:
    def __init__(self, stable_weight: int = 90, canary_weight: int = 10):
        self.stable_weight = stable_weight
        self.canary_weight = canary_weight

    def weights(self) -> Dict[str, int]:
        return {"stable": self.stable_weight, "canary": self.canary_weight}

    def promote(self) -> None:
        self.stable_weight = 100
        self.canary_weight = 0

    def rollback(self) -> None:
        self.stable_weight = 100
        self.canary_weight = 0
