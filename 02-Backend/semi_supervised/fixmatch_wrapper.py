import math
from typing import List, Dict, Any, Callable, Tuple


def _softmax_vector(vec: List[float], temperature: float) -> List[float]:
    max_val = max(vec)
    exps = [math.exp((v - max_val) / temperature) for v in vec]
    sum_exps = sum(exps)
    return [e / sum_exps for e in exps]


class FixMatchWrapper:
    def __init__(self, threshold: float = 0.95, temperature: float = 1.0, lambda_u: float = 1.0):
        self.threshold = threshold
        self.temperature = temperature
        self.lambda_u = lambda_u

    def pseudo_labels_from_weak(
        self,
        model: Callable[[List[List[float]]], List[List[float]]],
        weak_augmented_x: List[List[float]],
    ) -> Tuple[List[int], List[float]]:
        logits = model(weak_augmented_x)
        labels: List[int] = []
        mask: List[float] = []
        for logit in logits:
            probs = _softmax_vector(logit, self.temperature)
            max_prob = max(probs)
            label = probs.index(max_prob)
            if max_prob >= self.threshold:
                labels.append(label)
                mask.append(1.0)
            else:
                labels.append(-1)
                mask.append(0.0)
        return labels, mask

    def __call__(
        self,
        labeled_x: List[List[float]],
        labeled_y: List[int],
        unlabeled_x_weak: List[List[float]],
        unlabeled_x_strong: List[List[float]],
        model: Callable[[List[List[float]]], List[List[float]]],
        loss_fn: Callable[[List[List[float]], List[int]], float],
    ) -> Dict[str, Any]:
        labeled_logits = model(labeled_x)
        labeled_loss = loss_fn(labeled_logits, labeled_y)

        pseudo_labels, mask = self.pseudo_labels_from_weak(model, unlabeled_x_weak)
        unlabeled_logits = model(unlabeled_x_strong)

        unlabeled_loss = 0.0
        count = 0
        for logit, label, m in zip(unlabeled_logits, pseudo_labels, mask):
            if m > 0:
                probs = _softmax_vector(logit, self.temperature)
                target_prob = probs[label]
                unlabeled_loss += -math.log(target_prob + 1e-12)
                count += 1
        if count > 0:
            unlabeled_loss /= count

        total_loss = labeled_loss + self.lambda_u * unlabeled_loss
        return {
            "loss": total_loss,
            "labeled_loss": labeled_loss,
            "unlabeled_loss": unlabeled_loss,
            "mask": mask,
            "pseudo_labels": pseudo_labels,
        }
