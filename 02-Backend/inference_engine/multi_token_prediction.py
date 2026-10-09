
import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class MTPConfig:
    num_predictions: int = 3
    hidden_size: int = 128
    vocab_size: int = 1000
    shared_layer_id: int = 0

    def __post_init__(self):
        self.prediction_heads = []
        rng = np.random.default_rng(123)
        for i in range(self.num_predictions):
            weight = rng.standard_normal((self.vocab_size, self.hidden_size)).astype(np.float32) * 0.02
            bias = np.zeros(self.vocab_size, dtype=np.float32)
            self.prediction_heads.append((weight, bias))


@dataclass
class MTPModule:
    config: MTPConfig = field(default_factory=MTPConfig)

    def predict_next_k(self, hidden: np.ndarray, k: int) -> List[np.ndarray]:
        predictions = []
        current_hidden = hidden
        for i in range(min(k, len(self.config.prediction_heads))):
            weight, bias = self.config.prediction_heads[i]
            logits = current_hidden @ weight.T + bias
            predictions.append(logits)
            rng = np.random.default_rng(i + 1)
            current_hidden = rng.standard_normal(current_hidden.shape).astype(np.float32) * 0.1
        return predictions

    def forward(self, input_ids: np.ndarray, hidden: Optional[np.ndarray] = None) -> Dict:
        batch_size, seq_len = input_ids.shape if input_ids.ndim == 2 else (1, 1)
        if hidden is None:
            rng = np.random.default_rng(42)
            hidden = rng.standard_normal((batch_size, seq_len, self.config.hidden_size)).astype(np.float32) * 0.1
        predictions = self.predict_next_k(hidden, self.config.num_predictions)
        return {
            "hidden": hidden,
            "predictions": predictions,
            "num_predictions": len(predictions),
        }


class MultiTokenPredictor:
    def __init__(self, config: Optional[MTPConfig] = None):
        if config is None:
            config = MTPConfig()
        self.config = config
        self.mtp_module = MTPModule(config)
        self.accuracy_history: List[float] = []

    def training_step(self, input_ids: np.ndarray, target_ids: np.ndarray,
                      learning_rate: float = 0.001) -> Dict:
        forward_result = self.mtp_module.forward(input_ids)
        predictions = forward_result["predictions"]
        loss = 0.0
        correct = 0
        total = 0
        for i, pred_logits in enumerate(predictions):
            if i < len(target_ids):
                target = target_ids[i]
                probs = softmax(pred_logits)
                if probs.ndim > 1:
                    pred_token = int(np.argmax(probs[0]))
                else:
                    pred_token = int(np.argmax(probs))
                loss += -np.log(max(float(probs.flat[pred_token]), 1e-10))
                if pred_token == int(target):
                    correct += 1
                total += 1
        avg_loss = loss / max(total, 1)
        accuracy = correct / max(total, 1)
        self.accuracy_history.append(accuracy)
        return {
            "loss": avg_loss,
            "accuracy": accuracy,
            "num_predictions": len(predictions),
        }

    def predict(self, input_ids: List[int], num_steps: int = 3) -> List[int]:
        arr = np.array([input_ids], dtype=np.int64)
        result = self.mtp_module.forward(arr)
        predicted = []
        for logits in result["predictions"]:
            probs = softmax(logits)
            probs_1d = probs.reshape(-1)
            probs_1d = np.clip(probs_1d, 0, None)
            s = probs_1d.sum()
            if s > 0:
                probs_1d = probs_1d / s
            else:
                probs_1d = np.ones_like(probs_1d) / len(probs_1d)
            predicted.append(int(np.argmax(probs_1d)) % self.config.vocab_size)
        return predicted

    def get_training_stats(self) -> Dict:
        if not self.accuracy_history:
            return {"avg_accuracy": 0.0, "num_steps": 0}
        return {
            "avg_accuracy": float(np.mean(self.accuracy_history)),
            "num_steps": len(self.accuracy_history),
            "last_accuracy": self.accuracy_history[-1],
        }


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)
