import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any, List


@dataclass
class VAEConfig:
    input_dim: int
    latent_dim: int = 16
    hidden_dims: Tuple[int, ...] = (64, 32)
    beta: float = 1.0
    activation: str = "relu"


class VariationalAutoencoder:
    def __init__(self, config: VAEConfig):
        self.config = config
        self.encoder_params: Dict[str, np.ndarray] = {}
        self.decoder_params: Dict[str, np.ndarray] = {}
        self.loss_history: list = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        dims = [self.config.input_dim] + list(self.config.hidden_dims)
        for i in range(len(dims) - 1):
            self.encoder_params[f"W{i}"] = np.random.randn(dims[i], dims[i + 1]).astype(np.float64) * np.sqrt(2.0 / dims[i])
            self.encoder_params[f"b{i}"] = np.zeros(dims[i + 1], dtype=np.float64)
        self.encoder_params[f"W{len(dims)-1}_mu"] = np.random.randn(self.config.hidden_dims[-1], self.config.latent_dim).astype(np.float64) * np.sqrt(2.0 / self.config.hidden_dims[-1])
        self.encoder_params[f"b{len(dims)-1}_mu"] = np.zeros(self.config.latent_dim, dtype=np.float64)
        self.encoder_params[f"W{len(dims)-1}_logvar"] = np.random.randn(self.config.hidden_dims[-1], self.config.latent_dim).astype(np.float64) * np.sqrt(2.0 / self.config.hidden_dims[-1])
        self.encoder_params[f"b{len(dims)-1}_logvar"] = np.zeros(self.config.latent_dim, dtype=np.float64)

        dec_dims = [self.config.latent_dim] + list(reversed(self.config.hidden_dims)) + [self.config.input_dim]
        for i in range(len(dec_dims) - 1):
            self.decoder_params[f"W{i}"] = np.random.randn(dec_dims[i], dec_dims[i + 1]).astype(np.float64) * np.sqrt(2.0 / dec_dims[i])
            self.decoder_params[f"b{i}"] = np.zeros(dec_dims[i + 1], dtype=np.float64)

    @staticmethod
    def _activate(x: np.ndarray, name: str) -> np.ndarray:
        if name == "relu":
            return np.maximum(0, x)
        if name == "tanh":
            return np.tanh(x)
        if name == "sigmoid":
            return 1.0 / (1.0 + np.exp(-x))
        raise ValueError(f"Unsupported activation: {name}")

    @staticmethod
    def _activate_grad(x: np.ndarray, name: str) -> np.ndarray:
        if name == "relu":
            return (x > 0).astype(np.float64)
        if name == "tanh":
            return 1.0 - np.tanh(x) ** 2
        if name == "sigmoid":
            s = 1.0 / (1.0 + np.exp(-x))
            return s * (1.0 - s)
        raise ValueError(f"Unsupported activation: {name}")

    def _encode(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray]]:
        h = x
        acts: List[np.ndarray] = [h]
        keys = sorted([k for k in self.encoder_params if not k.endswith("_mu") and not k.endswith("_logvar")], key=lambda k: int(k[1:]))
        i = 0
        while i < len(keys):
            w = self.encoder_params[keys[i]]
            b = self.encoder_params[keys[i + 1]]
            h = self._activate(h @ w + b, self.config.activation)
            acts.append(h)
            i += 2
        n_mid = len(keys) // 2
        mu = h @ self.encoder_params[f"W{n_mid}_mu"] + self.encoder_params[f"b{n_mid}_mu"]
        logvar = h @ self.encoder_params[f"W{n_mid}_logvar"] + self.encoder_params[f"b{n_mid}_logvar"]
        return mu, logvar, acts

    @staticmethod
    def reparameterize(mu: np.ndarray, logvar: np.ndarray) -> np.ndarray:
        eps = np.random.randn(*mu.shape)
        return mu + np.exp(0.5 * logvar) * eps

    def _decode(self, z: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        h = z
        acts: List[np.ndarray] = [h]
        keys = sorted(self.decoder_params.keys(), key=lambda k: int(k[1:]))
        i = 0
        while i < len(keys):
            w = self.decoder_params[keys[i]]
            b = self.decoder_params[keys[i + 1]]
            h = self._activate(h @ w + b, self.config.activation)
            acts.append(h)
            i += 2
        return h, acts

    def reconstruct(self, x: np.ndarray) -> np.ndarray:
        mu, logvar, _ = self._encode(x)
        z = self.reparameterize(mu, logvar)
        x_hat, _ = self._decode(z)
        return x_hat

    def encode(self, x: np.ndarray) -> np.ndarray:
        mu, _, _ = self._encode(x)
        return mu

    def train_step(self, x: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        mu, logvar, enc_acts = self._encode(x)
        z = self.reparameterize(mu, logvar)
        x_hat, dec_acts = self._decode(z)
        recon = float(np.mean((x - x_hat) ** 2))
        kl = float(-0.5 * np.mean(1 + logvar - mu ** 2 - np.exp(logvar)))
        loss = recon + self.config.beta * kl
        self.loss_history.append(loss)

        d_xhat = 2.0 * (x_hat - x) / x.shape[0]
        dec_keys = sorted(self.decoder_params.keys(), key=lambda k: int(k[1:]))
        i = len(dec_keys) - 1
        grad = d_xhat
        while i >= 1:
            b_key = dec_keys[i]
            w_key = dec_keys[i - 1]
            w = self.decoder_params[w_key]
            h_prev = dec_acts[i // 2]
            db = np.sum(grad, axis=0)
            dw = h_prev.T @ grad
            grad = grad @ w.T * self._activate_grad(h_prev, self.config.activation)
            self.decoder_params[w_key] -= lr * dw
            self.decoder_params[b_key] -= lr * db
            i -= 2

        enc_keys = sorted([k for k in self.encoder_params if not k.endswith("_mu") and not k.endswith("_logvar")], key=lambda k: int(k[1:]))
        n_mid = len(enc_keys) // 2
        i = len(enc_keys) - 1
        grad = d_xhat
        while i >= 1:
            b_key = enc_keys[i]
            w_key = enc_keys[i - 1]
            h_prev = enc_acts[i // 2]
            db = np.sum(grad, axis=0)
            dw = h_prev.T @ grad
            grad = grad @ self.encoder_params[w_key].T * self._activate_grad(h_prev, self.config.activation)
            self.encoder_params[w_key] -= lr * dw
            self.encoder_params[b_key] -= lr * db
            i -= 2

        d_mu = grad @ self.encoder_params[f"W{n_mid}_mu"].T
        d_logvar = grad @ self.encoder_params[f"W{n_mid}_logvar"].T
        h_mid = enc_acts[n_mid // 2 + 1] if len(enc_acts) > (n_mid // 2 + 1) else enc_acts[-1]
        self.encoder_params[f"W{n_mid}_mu"] -= lr * h_mid.T @ d_mu
        self.encoder_params[f"b{n_mid}_mu"] -= lr * np.sum(d_mu, axis=0)
        self.encoder_params[f"W{n_mid}_logvar"] -= lr * h_mid.T @ d_logvar
        self.encoder_params[f"b{n_mid}_logvar"] -= lr * np.sum(d_logvar, axis=0)

        return {"loss": loss, "reconstruction_error": recon, "kl_divergence": kl}

    def get_report(self) -> Dict[str, Any]:
        return {
            "num_steps": len(self.loss_history),
            "last_loss": float(self.loss_history[-1]) if self.loss_history else None,
            "mean_loss": float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            "latent_dim": self.config.latent_dim,
            "input_dim": self.config.input_dim,
            "beta": self.config.beta,
        }
