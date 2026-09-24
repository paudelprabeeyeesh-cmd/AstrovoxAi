import math
from typing import List, Tuple


class InputSanitizer:
    def __init__(self, max_norm: float = 1.0, clip_value: float = 2.0, per_feature: bool = True) -> None:
        self._max_norm = max_norm
        self._clip_value = clip_value
        self._per_feature = per_feature

    def l2_norm(self, vector: List[float]) -> float:
        return math.sqrt(sum(v * v for v in vector))

    def clip(self, vector: List[float], bound: float) -> List[float]:
        return [max(-bound, min(bound, v)) for v in vector]

    def normalize(self, vector: List[float]) -> List[float]:
        norm = self.l2_norm(vector)
        if norm < 1e-12:
            return [0.0] * len(vector)
        return [v / norm for v in vector]

    def sanitize(self, data: List[float]) -> List[float]:
        clipped = self.clip(data, self._clip_value)
        if self._per_feature:
            return clipped
        norm = self.l2_norm(clipped)
        if norm > self._max_norm and norm > 1e-12:
            return [v * (self._max_norm / norm) for v in clipped]
        return clipped

    def batch_sanitize(self, batch: List[List[float]]) -> List[List[float]]:
        return [self.sanitize(sample) for sample in batch]

    def feature_stats(self, dataset: List[List[float]]) -> Tuple[List[float], List[float]]:
        if not dataset:
            raise ValueError("dataset must not be empty")
        num_features = len(dataset[0])
        if any(len(sample) != num_features for sample in dataset):
            raise ValueError("all samples must have the same number of features")
        means = []
        sdevs = []
        for feat in range(num_features):
            values = [sample[feat] for sample in dataset]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            means.append(mean)
            sdevs.append(math.sqrt(variance))
        return means, sdevs

    def filter_outliers(self, data: List[float], std_threshold: float = 3.0) -> List[float]:
        if not data:
            return []
        mean = sum(data) / len(data)
        variance = sum((v - mean) ** 2 for v in data) / len(data)
        std = math.sqrt(variance)
        return [v for v in data if abs(v - mean) <= std_threshold * std]
