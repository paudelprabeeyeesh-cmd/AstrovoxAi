import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class Episode:
    support_x: List[List[float]]
    support_y: List[int]
    query_x: List[List[float]]
    query_y: List[int]
    n_way: int = 5
    k_shot: int = 1
    query_size: int = 5


class EpisodeSampler:
    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def sample_episode(
        self,
        x: List[List[float]],
        y: List[int],
        n_way: int = 5,
        k_shot: int = 1,
        query_size: int = 5,
    ) -> Episode:
        classes = sorted(set(y))
        if n_way > len(classes):
            raise ValueError(f"n_way ({n_way}) exceeds available classes ({len(classes)})")

        selected = self._rng.sample(classes, n_way)
        support_x_list: List[List[float]] = []
        support_y_list: List[int] = []
        query_x_list: List[List[float]] = []
        query_y_list: List[int] = []

        for cls_idx, cls in enumerate(selected):
            indices = [i for i, label in enumerate(y) if label == cls]
            if len(indices) < k_shot + query_size:
                raise ValueError(
                    f"Class {cls} has only {len(indices)} samples, need {k_shot + query_size}"
                )
            chosen = self._rng.sample(indices, k_shot + query_size)
            support_x_list.extend(x[i] for i in chosen[:k_shot])
            support_y_list.extend([cls_idx] * k_shot)
            query_x_list.extend(x[i] for i in chosen[k_shot:])
            query_y_list.extend([cls_idx] * query_size)

        return Episode(
            support_x=support_x_list,
            support_y=support_y_list,
            query_x=query_x_list,
            query_y=query_y_list,
            n_way=n_way,
            k_shot=k_shot,
            query_size=query_size,
        )

    def sample_batch(
        self,
        x: List[List[float]],
        y: List[int],
        n_way: int = 5,
        k_shot: int = 1,
        query_size: int = 5,
        batch_size: int = 1,
    ) -> List[Episode]:
        return [
            self.sample_episode(x, y, n_way, k_shot, query_size)
            for _ in range(batch_size)
        ]

    def stratified_split(
        self,
        x: List[List[float]],
        y: List[int],
        support_ratio: float = 0.5,
    ) -> Tuple[List[List[float]], List[int], List[List[float]], List[int]]:
        classes = sorted(set(y))
        support_x_list: List[List[float]] = []
        support_y_list: List[int] = []
        query_x_list: List[List[float]] = []
        query_y_list: List[int] = []

        for cls in classes:
            indices = [i for i, label in enumerate(y) if label == cls]
            self._rng.shuffle(indices)
            n_support = max(1, int(len(indices) * support_ratio))
            support_x_list.extend(x[i] for i in indices[:n_support])
            support_y_list.extend(y[i] for i in indices[:n_support])
            query_x_list.extend(x[i] for i in indices[n_support:])
            query_y_list.extend(y[i] for i in indices[n_support:])

        return support_x_list, support_y_list, query_x_list, query_y_list
