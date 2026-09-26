import logging
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatasetBalancingConfig:
    target_ratio: Optional[Dict[str, float]] = None
    max_oversample_factor: float = 5.0
    shuffle: bool = True
    seed: int = 42


@dataclass
class LabeledSample:
    id: str
    text: str
    label: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class DatasetBalancer:
    def __init__(self, config: Optional[DatasetBalancingConfig] = None):
        self.config = config or DatasetBalancingConfig()
        logger.info("Dataset balancer initialized")

    def _compute_distribution(self, samples: List[LabeledSample]) -> Dict[str, int]:
        return Counter(sample.label for sample in samples)

    def balance(self, samples: List[LabeledSample]) -> List[LabeledSample]:
        if not samples:
            return []
        distribution = self._compute_distribution(samples)
        if not distribution:
            return samples

        if self.config.target_ratio:
            max_count = max(distribution.values())
            target_counts = {
                label: int(max_count * ratio)
                for label, ratio in self.config.target_ratio.items()
            }
        else:
            max_count = max(distribution.values())
            target_counts = {label: max_count for label in distribution}

        result: List[LabeledSample] = []
        buckets: Dict[str, List[LabeledSample]] = {}
        for sample in samples:
            buckets.setdefault(sample.label, []).append(sample)

        rng = random.Random(self.config.seed)
        for label, target in target_counts.items():
            bucket = buckets.get(label, [])
            if not bucket:
                continue
            factor = min(target / len(bucket), self.config.max_oversample_factor)
            count = int(len(bucket) * factor)
            for _ in range(count):
                result.append(rng.choice(bucket))
            remainder = target - count
            if remainder > 0:
                result.extend(bucket[:remainder])

        if self.config.shuffle:
            rng.shuffle(result)
        return result

    def report(self, samples: List[LabeledSample]) -> Dict[str, Any]:
        distribution = self._compute_distribution(samples)
        total = len(samples)
        return {
            "total": total,
            "distribution": dict(distribution),
            "ratios": {label: count / max(total, 1) for label, count in distribution.items()},
        }
