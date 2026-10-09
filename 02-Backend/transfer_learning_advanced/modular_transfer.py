import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class ModularComponentType(Enum):
    ADAPTER = "adapter"
    PROMPT = "prompt"
    PREFIX = "prefix"
    LORA = "lora"


@dataclass
class AdapterConfig:
    input_dim: int
    adapter_dim: int = 8
    dropout: float = 0.1
    init_scale: float = 0.01


class AdapterModule:
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.W_down = np.random.randn(config.input_dim, config.adapter_dim).astype(np.float64) * config.init_scale
        self.b_down = np.zeros(config.adapter_dim, dtype=np.float64)
        self.W_up = np.random.randn(config.adapter_dim, config.input_dim).astype(np.float64) * config.init_scale
        self.b_up = np.zeros(config.input_dim, dtype=np.float64)
        self.scale: float = 1.0

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.W_down + self.b_down)
        return self.scale * (h @ self.W_up + self.b_up)

    def step(self, x: np.ndarray, grad_output: np.ndarray, lr: float = 0.01) -> None:
        h = self._relu(x @ self.W_down + self.b_down)
        dW_up = h.T @ grad_output
        db_up = np.sum(grad_output, axis=0)
        grad_h = grad_output @ self.W_up.T
        grad_h = grad_h * (h > 0)
        dW_down = x.T @ grad_h
        db_down = np.sum(grad_h, axis=0)
        self.W_up -= lr * dW_up
        self.b_up -= lr * db_up
        self.W_down -= lr * dW_down
        self.b_down -= lr * db_down

    def freeze(self) -> None:
        pass

    def unfreeze(self) -> None:
        pass

    def param_count(self) -> int:
        return self.W_down.size + self.b_down.size + self.W_up.size + self.b_up.size


@dataclass
class PromptTuningConfig:
    prompt_length: int = 10
    hidden_dim: int = 32
    init_scale: float = 0.01


class PromptTuningModule:
    def __init__(self, config: PromptTuningConfig):
        self.config = config
        self.prompt_embeddings = np.random.randn(config.prompt_length, config.hidden_dim).astype(np.float64) * config.init_scale
        self.soft_prompt: Optional[np.ndarray] = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        batch_size = len(x)
        prompt = np.tile(self.prompt_embeddings, (batch_size, 1, 1))
        return np.concatenate([prompt, x.reshape(batch_size, 1, -1)], axis=1)

    def step(self, grad: np.ndarray, lr: float = 0.01) -> None:
        self.prompt_embeddings -= lr * np.mean(grad, axis=0)

    def freeze(self) -> None:
        pass

    def unfreeze(self) -> None:
        pass

    def param_count(self) -> int:
        return self.prompt_embeddings.size


@dataclass
class ModularModelConfig:
    input_dim: int
    hidden_dim: int = 64
    output_dim: int = 5


class ModularTransferModel:
    def __init__(self, config: ModularModelConfig):
        self.config = config
        self.W = np.random.randn(config.input_dim, config.hidden_dim).astype(np.float64) * 0.1
        self.b = np.zeros(config.hidden_dim, dtype=np.float64)
        self.W_out = np.random.randn(config.hidden_dim, config.output_dim).astype(np.float64) * 0.1
        self.b_out = np.zeros(config.output_dim, dtype=np.float64)
        self.adapters: Dict[str, AdapterModule] = {}
        self.prompt_modules: Dict[str, PromptTuningModule] = {}
        self.frozen_base: bool = False

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def freeze_base(self) -> None:
        self.frozen_base = True

    def unfreeze_base(self) -> None:
        self.frozen_base = False

    def add_adapter(self, name: str, adapter_dim: int = 8) -> AdapterModule:
        cfg = AdapterConfig(input_dim=self.config.hidden_dim, adapter_dim=adapter_dim)
        adapter = AdapterModule(cfg)
        self.adapters[name] = adapter
        return adapter

    def add_prompt(self, name: str, prompt_length: int = 10) -> PromptTuningModule:
        cfg = PromptTuningConfig(prompt_length=prompt_length, hidden_dim=self.config.hidden_dim)
        prompt = PromptTuningModule(cfg)
        self.prompt_modules[name] = prompt
        return prompt

    def forward(self, x: np.ndarray, adapter_names: Optional[List[str]] = None) -> np.ndarray:
        h = self._relu(x @ self.W + self.b)
        if adapter_names:
            for a_name in adapter_names:
                if a_name in self.adapters:
                    h = h + self.adapters[a_name].forward(h)
        logits = h @ self.W_out + self.b_out
        return logits

    def compute_loss(self, logits: np.ndarray, y: np.ndarray) -> float:
        probs = self._softmax(logits)
        y_int = y.astype(int)
        return float(-np.mean(np.log(probs[np.arange(len(y_int)), y_int] + 1e-12)))

    def step(self, x: np.ndarray, y: np.ndarray, lr: float = 0.01, adapter_names: Optional[List[str]] = None) -> float:
        logits = self.forward(x, adapter_names=adapter_names)
        loss = self.compute_loss(logits, y)
        probs = self._softmax(logits)
        y_int = y.astype(int)
        grad = probs.copy()
        grad[np.arange(len(y_int)), y_int] -= 1
        grad /= len(y_int)
        h = self._relu(x @ self.W + self.b)
        if adapter_names:
            for a_name in adapter_names:
                if a_name in self.adapters:
                    h = h + self.adapters[a_name].forward(h)
        dW_out = h.T @ grad
        db_out = np.sum(grad, axis=0)
        dh = grad @ self.W_out.T
        dh = dh * (h > 0)
        if not self.frozen_base:
            dW = x.T @ dh
            db = np.sum(dh, axis=0)
            self.W -= lr * dW
            self.b -= lr * db
            self.W_out -= lr * dW_out
            self.b_out -= lr * db_out
        else:
            self.W_out -= lr * dW_out
            self.b_out -= lr * db_out
        if adapter_names:
            for a_name in adapter_names:
                if a_name in self.adapters:
                    h_raw = self._relu(x @ self.W + self.b)
                    self.adapters[a_name].step(h_raw, dh, lr=lr)
        return loss

    def total_trainable_params(self) -> int:
        total = 0
        if not self.frozen_base:
            total += self.W.size + self.b.size + self.W_out.size + self.b_out.size
        for a in self.adapters.values():
            total += a.param_count()
        for p in self.prompt_modules.values():
            total += p.param_count()
        return total
