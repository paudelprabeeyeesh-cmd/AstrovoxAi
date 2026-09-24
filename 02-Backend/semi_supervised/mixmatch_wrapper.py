import random
import math
from typing import List, Dict, Any, Callable, Tuple


def _softmax_vector(vec: List[float], temperature: float) -> List[float]:
    max_val = max(vec)
    exps = [math.exp((v - max_val) / temperature) for v in vec]
    sum_exps = sum(exps)
    return [e / sum_exps for e in exps]


def _mixup(
    inputs1: List[List[float]],
    inputs2: List[List[float]],
    labels1: List[Any],
    labels2: List[Any],
    alpha: float,
) -> Tuple[List[List[float]], List[Any]]:
    lam = random.betavariate(alpha, alpha)
    mixed_inputs = [
        [lam * a1 + (1.0 - lam) * a2 for a1, a2 in zip(x1, x2)]
        for x1, x2 in zip(inputs1, inputs2)
    ]
    mixed_labels = []
    for y1, y2 in zip(labels1, labels2):
        if isinstance(y1, list):
            mixed_labels.append([lam * a1 + (1.0 - lam) * a2 for a1, a2 in zip(y1, y2)])
        else:
            mixed_labels.append(lam * y1 + (1.0 - lam) * y2)
    return mixed_inputs, mixed_labels


class MixMatchWrapper:
    def __init__(self, num_augmentations: int = 2, alpha: float = 0.75, threshold: float = 0.95, temperature: float = 1.0):
        self.num_augmentations = num_augmentations
        self.alpha = alpha
        self.threshold = threshold
        self.temperature = temperature

    def _default_augment(self, x: List[float]) -> List[float]:
        return [v + random.gauss(0, 0.1) for v in x]

    def process(
        self,
        labeled_x: List[List[float]],
        labeled_y: List[int],
        unlabeled_x: List[List[float]],
        model: Callable[[List[List[float]]], List[List[float]]],
        augment_fn: Callable[[List[float]], List[float]] = None,
    ) -> Dict[str, Any]:
        if augment_fn is None:
            augment_fn = self._default_augment

        num_classes = len(set(labeled_y)) if labeled_y else 2
        one_hot = lambda y: [1.0 if i == y else 0.0 for i in range(num_classes)]

        labeled_aug_x: List[List[float]] = []
        labeled_aug_y: List[List[float]] = []
        for x, y in zip(labeled_x, labeled_y):
            for _ in range(self.num_augmentations):
                labeled_aug_x.append(augment_fn(x))
                labeled_aug_y.append(one_hot(y))

        unlabeled_aug_x: List[List[float]] = []
        unlabeled_aug_y: List[List[float]] = []
        for x in unlabeled_x:
            augs = [augment_fn(x) for _ in range(self.num_augmentations)]
            logits_list = [model([a])[0] for a in augs]
            probs_list = [_softmax_vector(l, self.temperature) for l in logits_list]
            avg_probs = [
                sum(p[i] for p in probs_list) / len(probs_list)
                for i in range(len(probs_list[0]))
            ]
            if max(avg_probs) >= self.threshold:
                for _ in range(self.num_augmentations):
                    unlabeled_aug_x.append(augment_fn(x))
                    unlabeled_aug_y.append(avg_probs)

        if not unlabeled_aug_x:
            return {
                "mixed_x": labeled_aug_x,
                "mixed_y": labeled_aug_y,
                "labeled_weight": 1.0,
                "unlabeled_weight": 0.0,
            }

        n = max(len(labeled_aug_x), len(unlabeled_aug_x))
        mixed_x: List[List[float]] = []
        mixed_y: List[Any] = []
        for i in range(n):
            l_idx = i % len(labeled_aug_x)
            u_idx = i % len(unlabeled_aug_x)
            mx, my = _mixup(
                [labeled_aug_x[l_idx]],
                [unlabeled_aug_x[u_idx]],
                [labeled_aug_y[l_idx]],
                [unlabeled_aug_y[u_idx]],
                self.alpha,
            )
            mixed_x.append(mx[0])
            mixed_y.append(my[0])

        labeled_weight = len(labeled_aug_x) / (len(labeled_aug_x) + len(unlabeled_aug_x))
        unlabeled_weight = len(unlabeled_aug_x) / (len(labeled_aug_x) + len(unlabeled_aug_x))
        return {
            "mixed_x": mixed_x,
            "mixed_y": mixed_y,
            "labeled_weight": labeled_weight,
            "unlabeled_weight": unlabeled_weight,
        }
