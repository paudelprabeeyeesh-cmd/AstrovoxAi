import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class FineTuningStrategy(Enum):
    FULL = "full"
    GRADUAL_UNFREEZING = "gradual_unfreezing"
    DISCRIMINATIVE_LR = "discriminative_lr"
    ADAPTER_ONLY = "adapter_only"
    LAYERWISE_DECAY = "layerwise_decay"


@dataclass
class LayerConfig:
    name: str
    params: Dict[str, np.ndarray]
    trainable: bool = True
    learning_rate_multiplier: float = 1.0


@dataclass
class FineTuningResult:
    strategy: str
    loss: float
    updated_layers: List[str] = field(default_factory=list)
    learning_rates: Dict[str, float] = field(default_factory=dict)


class FineTuningModel:
    def __init__(self, input_dim: int, hidden_dim: int = 32, output_dim: int = 5):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.layers: Dict[str, LayerConfig] = {}
        self.loss_history: List[float] = []
        self._initialize()

    def _initialize(self) -> None:
        self.layers["encoder"] = LayerConfig(
            name="encoder",
            params={
                "W": np.random.randn(self.input_dim, self.hidden_dim).astype(np.float64) * 0.1,
                "b": np.zeros(self.hidden_dim, dtype=np.float64)
            },
            trainable=True,
            learning_rate_multiplier=1.0
        )
        self.layers["head"] = LayerConfig(
            name="head",
            params={
                "W": np.random.randn(self.hidden_dim, self.output_dim).astype(np.float64) * 0.1,
                "b": np.zeros(self.output_dim, dtype=np.float64)
            },
            trainable=True,
            learning_rate_multiplier=1.0
        )

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        e = self._relu(x @ self.layers["encoder"].params["W"] + self.layers["encoder"].params["b"])
        logits = e @ self.layers["head"].params["W"] + self.layers["head"].params["b"]
        return e, logits

    def compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def freeze_layer(self, layer_name: str) -> None:
        if layer_name in self.layers:
            self.layers[layer_name].trainable = False

    def unfreeze_layer(self, layer_name: str) -> None:
        if layer_name in self.layers:
            self.layers[layer_name].trainable = True

    def set_learning_rate_multiplier(self, layer_name: str, multiplier: float) -> None:
        if layer_name in self.layers:
            self.layers[layer_name].learning_rate_multiplier = multiplier

    def get_trainable_layers(self) -> List[str]:
        return [name for name, cfg in self.layers.items() if cfg.trainable]

    def step(self, x: np.ndarray, y: np.ndarray, base_lr: float = 0.01) -> float:
        h, logits = self.forward(x)
        loss = self.compute_loss(logits, y)
        self.loss_history.append(loss)
        probs = self._softmax(logits)
        y_int = y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        dW_head = h.T @ grad
        db_head = np.sum(grad, axis=0)
        dh = grad @ self.layers["head"].params["W"].T
        dh = dh * (h > 0)
        dW_enc = x.T @ dh
        db_enc = np.sum(dh, axis=0)

        if self.layers["head"].trainable:
            lr_h = base_lr * self.layers["head"].learning_rate_multiplier
            self.layers["head"].params["W"] -= lr_h * dW_head
            self.layers["head"].params["b"] -= lr_h * db_head
        if self.layers["encoder"].trainable:
            lr_e = base_lr * self.layers["encoder"].learning_rate_multiplier
            self.layers["encoder"].params["W"] -= lr_e * dW_enc
            self.layers["encoder"].params["b"] -= lr_e * db_enc
        return loss


class GradualUnfreezing:
    def __init__(self, model: FineTuningModel, unfreeze_every: int = 1):
        self.model = model
        self.unfreeze_every = unfreeze_every
        self.current_epoch = 0
        self.unfrozen_count = 0
        self.layer_order = list(reversed(list(model.layers.keys())))

    def before_epoch(self) -> None:
        self.current_epoch += 1
        if self.current_epoch % self.unfreeze_every == 0 and self.unfrozen_count < len(self.layer_order):
            layer = self.layer_order[self.unfrozen_count]
            self.model.unfreeze_layer(layer)
            self.unfrozen_count += 1

    def get_frozen_layers(self) -> List[str]:
        return [name for name in self.model.layers if not self.model.layers[name].trainable]


class DiscriminativeLR:
    def __init__(self, model: FineTuningModel, base_lr: float = 0.01, decay: float = 0.5):
        self.model = model
        self.base_lr = base_lr
        self.decay = decay
        self._configure()

    def _configure(self) -> None:
        layer_names = list(self.model.layers.keys())
        for i, name in enumerate(layer_names):
            mult = self.decay ** (len(layer_names) - 1 - i)
            self.model.set_learning_rate_multiplier(name, mult)

    def get_learning_rates(self) -> Dict[str, float]:
        return {
            name: self.base_lr * cfg.learning_rate_multiplier
            for name, cfg in self.model.layers.items()
        }


class LayerwiseDecay:
    def __init__(self, decay_factor: float = 0.95):
        self.decay_factor = decay_factor

    def apply(self, model: FineTuningModel, base_lr: float = 0.01) -> Dict[str, float]:
        layer_names = list(model.layers.keys())
        lrs = {}
        for i, name in enumerate(layer_names):
            lr = base_lr * (self.decay_factor ** (len(layer_names) - 1 - i))
            model.set_learning_rate_multiplier(name, lr / base_lr)
            lrs[name] = lr
        return lrs


class AdapterFineTuning:
    def __init__(self, model: FineTuningModel, adapter_dim: int = 8):
        self.model = model
        self.adapter_dim = adapter_dim
        self.adapters: Dict[str, Dict[str, np.ndarray]] = {}
        self.freeze_base_model()

    def freeze_base_model(self) -> None:
        for name in self.model.layers:
            self.model.freeze_layer(name)

    def add_adapter(self, layer_name: str) -> None:
        if layer_name not in self.model.layers:
            return
        cfg = self.model.layers[layer_name]
        out_dim = cfg.params["W"].shape[1] if "W" in cfg.params else self.model.hidden_dim
        in_dim = cfg.params["W"].shape[0] if "W" in cfg.params else self.model.hidden_dim
        self.adapters[layer_name] = {
            "W_down": np.random.randn(in_dim, self.adapter_dim).astype(np.float64) * 0.01,
            "b_down": np.zeros(self.adapter_dim, dtype=np.float64),
            "W_up": np.random.randn(self.adapter_dim, out_dim).astype(np.float64) * 0.01,
            "b_up": np.zeros(out_dim, dtype=np.float64)
        }

    def adapter_forward(self, x: np.ndarray, layer_name: str) -> np.ndarray:
        if layer_name not in self.adapters:
            return x
        a = self.adapters[layer_name]
        h = np.maximum(0, x @ a["W_down"] + a["b_down"])
        return x + h @ a["W_up"] + a["b_up"]

    def count_trainable_params(self) -> int:
        total = 0
        for a in self.adapters.values():
            for v in a.values():
                total += v.size
        return total
