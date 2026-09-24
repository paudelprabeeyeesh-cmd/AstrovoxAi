import numpy as np
from typing import Dict, List, Optional, Any


class AdvancedActiveLearner:
    def __init__(self, strategy: str = 'uncertainty', num_classes: int = 2,
                 acquisition: str = 'max_entropy', batch_size: int = 1):
        self.strategy = strategy
        self.num_classes = num_classes
        self.acquisition = acquisition
        self.batch_size = batch_size
        self.labeled_x: np.ndarray = np.empty((0, 0))
        self.labeled_y: np.ndarray = np.empty((0,), dtype=int)
        self.unlabeled_x: Optional[np.ndarray] = None
        self.unlabeled_indices: np.ndarray = np.empty(0, dtype=int)
        self.query_log: List[Dict[str, Any]] = []
        self.loss_history: List[float] = []
        self.acquisition_scores: List[float] = []
        self.iteration_count: int = 0
        self.f1_history: List[float] = []

    def initialize(self, x: np.ndarray, initial_labels: Optional[np.ndarray] = None) -> None:
        self.unlabeled_x = x
        self.unlabeled_indices = np.arange(len(x))
        if initial_labels is not None and len(initial_labels) > 0:
            self.labeled_x = x[initial_labels != -1] if -1 in initial_labels else x[:1]
            self.labeled_y = initial_labels[initial_labels != -1] if -1 in initial_labels else initial_labels[:1]
            mask = np.ones(len(x), dtype=bool)
            if -1 in initial_labels:
                mask[initial_labels != -1] = False
            self.unlabeled_indices = np.where(mask)[0]
            self.unlabeled_x = x[mask]

    def query(self, model: Any, batch_size: int = 1) -> List[int]:
        batch_size = batch_size if batch_size > 0 else self.batch_size
        if self.acquisition == 'max_entropy':
            return self._max_entropy(model, batch_size)
        elif self.acquisition == 'bald':
            return self._bald(model, batch_size)
        elif self.acquisition == 'margin':
            return self._margin(model, batch_size)
        elif self.acquisition == 'confidence':
            return self._confidence(model, batch_size)
        else:
            return self._random(model, batch_size)

    def _get_scores(self, model: Any) -> np.ndarray:
        if hasattr(model, 'predict_proba'):
            return model.predict_proba(self.unlabeled_x)
        elif hasattr(model, 'classify'):
            preds = model.classify(self.unlabeled_x)
            preds_int = preds.astype(int) % self.num_classes
            probs = np.zeros((len(self.unlabeled_x), self.num_classes))
            for i in range(len(preds_int)):
                probs[i, preds_int[i] % self.num_classes] = 1.0
            return probs
        elif hasattr(model, '_forward'):
            _, logits = model._forward(self.unlabeled_x)
            e = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            return e / np.sum(e, axis=1, keepdims=True)
        return np.random.rand(len(self.unlabeled_x), self.num_classes)

    def _max_entropy(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        eps = 1e-12
        entropy = -np.sum(proba * np.log(proba + eps), axis=1)
        indices = np.argsort(entropy)[::-1][:batch_size]
        scores = entropy[indices]
        self.acquisition_scores.extend(scores.tolist())
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _bald(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        eps = 1e-12
        entropy = -np.sum(proba * np.log(proba + eps), axis=1)
        y_prob = np.mean(proba, axis=1)
        cond_entropy = -np.sum(y_prob[:, None] * np.log(proba + eps), axis=1)
        mutual_info = entropy - cond_entropy
        indices = np.argsort(mutual_info)[::-1][:batch_size]
        self.acquisition_scores.extend(mutual_info[indices].tolist())
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _margin(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        sorted_proba = np.sort(proba, axis=1)
        margin = sorted_proba[:, -1] - sorted_proba[:, -2]
        indices = np.argsort(margin)[:batch_size]
        self.acquisition_scores.extend(margin[indices].tolist())
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _confidence(self, model: Any, batch_size: int) -> List[int]:
        proba = self._get_scores(model)
        confidence = np.max(proba, axis=1)
        indices = np.argsort(confidence)[:batch_size]
        self.acquisition_scores.extend(confidence[indices].tolist())
        return [int(self.unlabeled_indices[i]) for i in indices]

    def _random(self, model: Any, batch_size: int) -> List[int]:
        if len(self.unlabeled_indices) == 0:
            return []
        indices = np.random.choice(len(self.unlabeled_indices), size=min(batch_size, len(self.unlabeled_indices)), replace=False)
        return [int(self.unlabeled_indices[i]) for i in indices]

    def update_labels(self, indices: List[int], labels: np.ndarray) -> None:
        for idx, label in zip(indices, labels):
            self.query_log.append({'index': int(idx), 'label': int(label)})
            if idx in self.unlabeled_indices:
                pos = np.where(self.unlabeled_indices == idx)[0]
                if len(pos) > 0:
                    self.unlabeled_indices = np.delete(self.unlabeled_indices, pos[0])
        if len(self.unlabeled_indices) == 0:
            self.unlabeled_x = np.empty((0, self.unlabeled_x.shape[1])) if self.unlabeled_x is not None else np.empty((0, 0))
        self.iteration_count += 1

    def get_query_efficiency(self) -> Dict[str, Any]:
        return {
            'labeled_count': len(self.labeled_y),
            'unlabeled_count': len(self.unlabeled_indices),
            'queries': len(self.query_log),
            'strategy': self.acquisition,
            'iterations': self.iteration_count,
        }

    def evaluate(self, model: Any, x_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        if hasattr(model, 'classify'):
            preds = model.classify(x_test)
        elif hasattr(model, '_forward'):
            _, logits = model._forward(x_test)
            preds = np.argmax(logits, axis=1)
        else:
            preds = np.random.randint(0, self.num_classes, size=len(y_test))
        preds = preds.astype(int) % self.num_classes
        y_test = y_test.astype(int)
        tp = float(np.sum((preds == 1) & (y_test == 1)))
        fp = float(np.sum((preds == 1) & (y_test == 0)))
        fn = float(np.sum((preds == 0) & (y_test == 1)))
        precision = tp / (tp + fp + 1e-12)
        recall = tp / (tp + fn + 1e-12)
        f1 = 2 * precision * recall / (precision + recall + 1e-12)
        self.f1_history.append(f1)
        return {'accuracy': float(np.mean(preds == y_test)), 'f1': f1, 'precision': precision, 'recall': recall}

