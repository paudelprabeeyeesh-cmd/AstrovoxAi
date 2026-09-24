import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple


@dataclass
class ModalityEmbedding:
    embedding: np.ndarray
    modality: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class CrossModalAttention:
    def __init__(self, embed_dim: int = 256, num_heads: int = 4):
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        self._rng = np.random.default_rng(42)
        self.W_q = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02
        self.W_k = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02
        self.W_v = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02
        self.W_o = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02

    def forward(self, query: np.ndarray, key: np.ndarray, value: np.ndarray) -> np.ndarray:
        q = query @ self.W_q
        k = key @ self.W_k
        v = value @ self.W_v
        if q.ndim == 2:
            q = q[np.newaxis, ...]
        if k.ndim == 2:
            k = k[np.newaxis, ...]
        if v.ndim == 2:
            v = v[np.newaxis, ...]
        q = self._split_heads(q)
        k = self._split_heads(k)
        v = self._split_heads(v)
        attn_output = self._scaled_dot_product_attention(q, k, v)
        attn_output = self._combine_heads(attn_output)
        return (attn_output @ self.W_o).squeeze(0)

    def _split_heads(self, x: np.ndarray) -> np.ndarray:
        batch, seq_len, _ = x.shape
        return x.reshape(batch, seq_len, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)

    def _combine_heads(self, x: np.ndarray) -> np.ndarray:
        batch, num_heads, seq_len, head_dim = x.shape
        return x.transpose(0, 2, 1, 3).reshape(batch, seq_len, self.num_heads * head_dim)

    def _scaled_dot_product_attention(self, q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
        d_k = q.shape[-1]
        scores = (q @ k.transpose(0, 1, 3, 2)) / np.sqrt(d_k)
        attn = self._softmax(scores)
        return attn @ v

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e / e.sum(axis=-1, keepdims=True)


class ModalityFusion:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self._rng = np.random.default_rng(42)
        self.W_early = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02
        self.W_late = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02
        self.W_hybrid = self._rng.standard_normal((2 * embed_dim, embed_dim)) * 0.02

    def early_fusion(self, text_emb: np.ndarray, image_emb: np.ndarray, audio_emb: Optional[np.ndarray] = None) -> np.ndarray:
        modalities = [text_emb, image_emb]
        if audio_emb is not None:
            modalities.append(audio_emb)
        concat = np.concatenate(modalities, axis=-1)
        if concat.shape[-1] > self.embed_dim:
            concat = concat[: self.embed_dim]
        elif concat.shape[-1] < self.embed_dim:
            concat = np.pad(concat, (0, self.embed_dim - concat.shape[-1]))
        return np.tanh(concat @ self.W_early)

    def late_fusion(self, text_emb: np.ndarray, image_emb: np.ndarray, audio_emb: Optional[np.ndarray] = None) -> np.ndarray:
        text_proj = text_emb @ self.W_late
        image_proj = image_emb @ self.W_late
        modalities = [text_proj, image_proj]
        if audio_emb is not None:
            audio_proj = audio_emb @ self.W_late
            modalities.append(audio_proj)
        return np.mean(modalities, axis=0)

    def hybrid_fusion(self, text_emb: np.ndarray, image_emb: np.ndarray, audio_emb: Optional[np.ndarray] = None) -> np.ndarray:
        early = self.early_fusion(text_emb, image_emb, audio_emb)
        late = self.late_fusion(text_emb, image_emb, audio_emb)
        concat = np.concatenate([early, late])
        if len(concat) < 2 * self.embed_dim:
            concat = np.pad(concat, (0, 2 * self.embed_dim - len(concat)))
        return np.tanh(concat[: 2 * self.embed_dim] @ self.W_hybrid)


class ModalityAlignment:
    def __init__(self, embed_dim: int = 256):
        self.embed_dim = embed_dim
        self._rng = np.random.default_rng(42)

    def canonical_correlation(self, X: np.ndarray, Y: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        X = X - X.mean(axis=0)
        Y = Y - Y.mean(axis=0)
        n_x, d_x = X.shape
        n_y, d_y = Y.shape
        k = min(k, d_x, d_y)
        if n_x < d_x:
            K_x = X @ X.T
            K_y = Y @ Y.T
            K_xy = X @ Y.T
            K_xy_t = Y @ X.T
            d1, d2 = n_x, n_y
        else:
            K_x = X.T @ X
            K_y = Y.T @ Y
            K_xy = X.T @ Y
            K_xy_t = Y.T @ X
            d1, d2 = d_x, d_y
        C_kk = K_x + 1e-5 * np.eye(d1)
        C_ll = K_y + 1e-5 * np.eye(d2)
        C_kl = K_xy
        C_kl_t = K_xy_t
        C_kk_inv = np.linalg.inv(C_kk)
        C_ll_inv = np.linalg.inv(C_ll)
        M = C_kk_inv @ C_kl @ C_ll_inv @ C_kl_t
        eigvals, eigvecs = np.linalg.eigh(M)
        idx = np.argsort(eigvals)[::-1][:k]
        if n_x < d_x:
            w_x = X.T @ eigvecs[:, idx]
        else:
            w_x = eigvecs[:, idx]
        if n_y < d_y:
            w_y = Y.T @ eigvecs[:, idx]
        else:
            w_y = eigvecs[:, idx]
        w_x = w_x / (np.linalg.norm(w_x, axis=0, keepdims=True) + 1e-8)
        w_y = w_y / (np.linalg.norm(w_y, axis=0, keepdims=True) + 1e-8)
        return w_x, w_y

    def compute_alignment_score(self, X: np.ndarray, Y: np.ndarray) -> float:
        n_x, d_x = X.shape
        n_y, d_y = Y.shape
        k = min(3, d_x, d_y)
        if k == 0:
            return 0.0
        w_x, w_y = self.canonical_correlation(X, Y, k=k)
        proj_x = X @ w_x
        proj_y = Y @ w_y
        corrs = []
        for i in range(proj_x.shape[1]):
            if proj_x[:, i].std() > 1e-8 and proj_y[:, i].std() > 1e-8:
                c = np.corrcoef(proj_x[:, i], proj_y[:, i])[0, 1]
                if not np.isnan(c):
                    corrs.append(abs(c))
        score = float(np.mean(corrs)) if corrs else 0.0
        return float(np.clip(score, -1.0, 1.0))

    def align_modalities(self, embeddings: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        keys = list(embeddings.keys())
        if len(keys) < 2:
            return embeddings
        aligned = {}
        for i, key_i in enumerate(keys):
            for j, key_j in enumerate(keys):
                if i >= j:
                    continue
                score = self.compute_alignment_score(embeddings[key_i], embeddings[key_j])
                aligned[f"{key_i}_{key_j}"] = np.array([score])
        return aligned


class MultimodalTransformer:
    def __init__(self, embed_dim: int = 256, num_layers: int = 2):
        self.embed_dim = embed_dim
        self.num_layers = num_layers
        self._rng = np.random.default_rng(42)
        self.attention_layers = [CrossModalAttention(embed_dim) for _ in range(num_layers)]
        self.W_out = self._rng.standard_normal((embed_dim, embed_dim)) * 0.02

    def forward(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        all_embs = []
        for modality, emb in inputs.items():
            if emb.ndim == 1:
                emb = emb.reshape(1, -1)
            all_embs.append(emb)
        max_len = max(e.shape[0] for e in all_embs)
        padded = []
        for emb in all_embs:
            if emb.shape[0] < max_len:
                pad_width = ((0, max_len - emb.shape[0]), (0, 0))
                emb = np.pad(emb, pad_width, mode="constant")
            padded.append(emb[:max_len])
        combined = np.mean(padded, axis=0)
        for layer in self.attention_layers:
            combined = layer.forward(combined, combined, combined)
        return np.tanh(combined @ self.W_out).mean(axis=0)
