import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class RepConfig:
    input_dim: int
    latent_dim: int = 32
    hidden_dims: Tuple[int, ...] = (128, 64)


class RepresentationLearner:
    def __init__(self, config: RepConfig):
        self.config = config
        self.encoder_params: Dict[str, np.ndarray] = {}
        self.decoder_params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        dims = [self.config.input_dim] + list(self.config.hidden_dims) + [self.config.latent_dim]
        for i in range(len(dims) - 1):
            self.encoder_params[f'W{i}'] = np.random.randn(dims[i], dims[i + 1]).astype(np.float64) * np.sqrt(2.0 / dims[i])
            self.encoder_params[f'b{i}'] = np.zeros(dims[i + 1], dtype=np.float64)
        dec_dims = list(reversed(dims))
        for i in range(len(dec_dims) - 1):
            self.decoder_params[f'W{i}'] = np.random.randn(dec_dims[i], dec_dims[i + 1]).astype(np.float64) * np.sqrt(2.0 / dec_dims[i])
            self.decoder_params[f'b{i}'] = np.zeros(dec_dims[i + 1], dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _relu_grad(x: np.ndarray) -> np.ndarray:
        return (x > 0).astype(np.float64)

    def _encode_forward(self, x: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        h = x
        acts: List[np.ndarray] = [h]
        keys = sorted(self.encoder_params.keys(), key=lambda k: int(k[1:]))
        i = 0
        while i < len(keys):
            w = self.encoder_params[keys[i]]
            b = self.encoder_params[keys[i + 1]]
            h = self._relu(h @ w + b)
            acts.append(h)
            i += 2
        return h, acts

    def _decode_forward(self, z: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        h = z
        acts: List[np.ndarray] = [h]
        keys = sorted(self.decoder_params.keys(), key=lambda k: int(k[1:]))
        i = 0
        while i < len(keys):
            w = self.decoder_params[keys[i]]
            b = self.decoder_params[keys[i + 1]]
            h = self._relu(h @ w + b)
            acts.append(h)
            i += 2
        return h, acts

    def train_step(self, x: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        z, enc_acts = self._encode_forward(x)
        x_hat, dec_acts = self._decode_forward(z)
        loss = float(np.mean((x - x_hat) ** 2))
        self.loss_history.append(loss)
        d_xhat = 2.0 * (x_hat - x) / x.shape[0]
        keys = sorted(self.decoder_params.keys(), key=lambda k: int(k[1:]))
        i = len(keys) - 1
        grad = d_xhat
        while i >= 1:
            b_key = keys[i]
            w_key = keys[i - 1]
            b = self.decoder_params[b_key]
            w = self.decoder_params[w_key]
            h_prev = dec_acts[i // 2]
            db = np.sum(grad, axis=0)
            dw = h_prev.T @ grad
            dh = grad @ w.T * self._relu_grad(h_prev)
            self.decoder_params[w_key] -= lr * dw
            self.decoder_params[b_key] -= lr * db
            grad = dh
            i -= 2
        enc_keys = sorted(self.encoder_params.keys(), key=lambda k: int(k[1:]))
        i = len(enc_keys) - 1
        while i >= 1:
            b_key = enc_keys[i]
            w_key = enc_keys[i - 1]
            b = self.encoder_params[b_key]
            w = self.encoder_params[w_key]
            h_prev = enc_acts[i // 2]
            db = np.sum(grad, axis=0)
            dw = h_prev.T @ grad
            dh = grad @ w.T * self._relu_grad(h_prev)
            self.encoder_params[w_key] -= lr * dw
            self.encoder_params[b_key] -= lr * db
            grad = dh
            i -= 2
        return {'loss': loss, 'reconstruction_error': loss}

    def _encode(self, x: np.ndarray) -> np.ndarray:
        h, _ = self._encode_forward(x)
        return h

    def extract_features(self, x: np.ndarray) -> np.ndarray:
        return self._encode(x)

    def reduce_dimensions(self, x: np.ndarray, n_components: int) -> np.ndarray:
        z = self._encode(x)
        if n_components >= z.shape[1]:
            return z
        _, _, vt = np.linalg.svd(z, full_matrices=False)
        return z @ vt[:n_components].T

    def compute_representation_similarity(self, x: np.ndarray) -> np.ndarray:
        z = self._encode(x)
        z = z / (np.linalg.norm(z, axis=1, keepdims=True) + 1e-12)
        return z @ z.T

    def get_report(self) -> Dict[str, Any]:
        return {
            'num_steps': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'latent_dim': self.config.latent_dim,
            'input_dim': self.config.input_dim,
        }
