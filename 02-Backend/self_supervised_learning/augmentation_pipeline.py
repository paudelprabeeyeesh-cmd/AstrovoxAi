import random
import math
from dataclasses import dataclass
from typing import Callable, List, Optional

Vector = List[float]


@dataclass
class GaussianNoise:
    std: float = 0.01
    seed: Optional[int] = None

    def __call__(self, x: Vector) -> Vector:
        rng = random.Random(self.seed)
        return [v + rng.gauss(0.0, self.std) for v in x]


@dataclass
class Dropout:
    p: float = 0.1
    seed: Optional[int] = None

    def __call__(self, x: Vector) -> Vector:
        rng = random.Random(self.seed)
        return [0.0 if rng.random() < self.p else v for v in x]


@dataclass
class RandomRescale:
    low: float = 0.8
    high: float = 1.2
    seed: Optional[int] = None

    def __call__(self, x: Vector) -> Vector:
        rng = random.Random(self.seed)
        scale = rng.uniform(self.low, self.high)
        return [v * scale for v in x]


@dataclass
class AugmentationPipeline:
    transforms: List[Callable[[Vector], Vector]]

    def __call__(self, x: Vector) -> Vector:
        result = list(x)
        for t in self.transforms:
            result = t(result)
        return result

    def append(self, transform: Callable[[Vector], Vector]) -> None:
        self.transforms.append(transform)


DEFAULT_PIPELINE = AugmentationPipeline(transforms=[GaussianNoise(std=0.01), Dropout(p=0.1)])
