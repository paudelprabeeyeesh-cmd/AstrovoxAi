import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import random


@dataclass
class Episode:
    support_x: np.ndarray
    support_y: np.ndarray
    query_x: np.ndarray
    query_y: np.ndarray
    n_way: int = 5
    k_shot: int = 1
    query_size: int = 5


class EpisodeSampler:
    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def sample_episode(
        self,
        x: np.ndarray,
        y: np.ndarray,
        n_way: int = 5,
        k_shot: int = 1,
        query_size: int = 5
    ) -> Episode:
        classes = sorted(np.unique(y))
        if n_way > len(classes):
            raise ValueError(f"n_way ({n_way}) exceeds available classes ({len(classes)})")

        selected = self._rng.sample(classes, n_way)
        support_x_list = []
        support_y_list = []
        query_x_list = []
        query_y_list = []

        for cls_idx, cls in enumerate(selected):
            mask = y == cls
            class_x = x[mask]
            if len(class_x) < k_shot + query_size:
                raise ValueError(f"Class {cls} has only {len(class_x)} samples, need {k_shot + query_size}")
            indices = self._rng.sample(range(len(class_x)), k_shot + query_size)
            support_x_list.append(class_x[indices[:k_shot]])
            support_y_list.append(np.full(k_shot, cls_idx, dtype=int))
            query_x_list.append(class_x[indices[k_shot:]])
            query_y_list.append(np.full(query_size, cls_idx, dtype=int))

        support_x = np.concatenate(support_x_list, axis=0)
        support_y = np.concatenate(support_y_list, axis=0)
        query_x = np.concatenate(query_x_list, axis=0)
        query_y = np.concatenate(query_y_list, axis=0)

        return Episode(
            support_x=support_x,
            support_y=support_y,
            query_x=query_x,
            query_y=query_y,
            n_way=n_way,
            k_shot=k_shot,
            query_size=query_size
        )

    def sample_batch(
        self,
        x: np.ndarray,
        y: np.ndarray,
        n_way: int = 5,
        k_shot: int = 1,
        query_size: int = 5,
        batch_size: int = 1
    ) -> List[Episode]:
        return [self.sample_episode(x, y, n_way, k_shot, query_size) for _ in range(batch_size)]

    def stratified_split(
        self,
        x: np.ndarray,
        y: np.ndarray,
        support_ratio: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        classes = sorted(np.unique(y))
        support_x_list = []
        support_y_list = []
        query_x_list = []
        query_y_list = []

        for cls in classes:
            mask = y == cls
            class_x = x[mask]
            class_y = y[mask]
            n_support = max(1, int(len(class_x) * support_ratio))
            indices = self._rng.sample(range(len(class_x)), len(class_x))
            support_x_list.append(class_x[indices[:n_support]])
            support_y_list.append(class_y[indices[:n_support]])
            query_x_list.append(class_x[indices[n_support:]])
            query_y_list.append(class_y[indices[n_support:]])

        return (
            np.concatenate(support_x_list),
            np.concatenate(support_y_list),
            np.concatenate(query_x_list),
            np.concatenate(query_y_list)
        )
