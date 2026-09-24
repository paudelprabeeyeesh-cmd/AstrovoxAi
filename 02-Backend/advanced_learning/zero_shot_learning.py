import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class CLIPConfig:
    visual_input_dim: int
    text_input_dim: int
    embedding_dim: int = 256
    temperature: float = 0.07
    hidden_dim: int = 256


class ZeroShotLearner:
    def __init__(self, config: CLIPConfig):
        self.config = config
        self.visual_params: Dict[str, np.ndarray] = {}
        self.text_params: Dict[str, np.ndarray] = {}
        self.loss_history: List[float] = []
        self._initialize_params()

    def _initialize_params(self) -> None:
        vi = self.config.visual_input_dim
        ti = self.config.text_input_dim
        h = self.config.hidden_dim
        e = self.config.embedding_dim
        self.visual_params['W1'] = np.random.randn(vi, h).astype(np.float64) * np.sqrt(2.0 / vi)
        self.visual_params['b1'] = np.zeros(h, dtype=np.float64)
        self.visual_params['W2'] = np.random.randn(h, e).astype(np.float64) * np.sqrt(2.0 / h)
        self.visual_params['b2'] = np.zeros(e, dtype=np.float64)
        self.text_params['W1'] = np.random.randn(ti, h).astype(np.float64) * np.sqrt(2.0 / ti)
        self.text_params['b1'] = np.zeros(h, dtype=np.float64)
        self.text_params['W2'] = np.random.randn(h, e).astype(np.float64) * np.sqrt(2.0 / h)
        self.text_params['b2'] = np.zeros(e, dtype=np.float64)
        self.logit_scale = np.array(1.0, dtype=np.float64)

    @staticmethod
    def _relu(x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e / np.sum(e, axis=1, keepdims=True)

    def _encode_visual(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.visual_params['W1'] + self.visual_params['b1'])
        return h @ self.visual_params['W2'] + self.visual_params['b2']

    def _encode_text(self, x: np.ndarray) -> np.ndarray:
        h = self._relu(x @ self.text_params['W1'] + self.text_params['b1'])
        return h @ self.text_params['W2'] + self.text_params['b2']

    def _nt_xent_loss(self, image_embeddings: np.ndarray, text_embeddings: np.ndarray) -> float:
        N = len(image_embeddings)
        image_embeddings = image_embeddings / (np.linalg.norm(image_embeddings, axis=1, keepdims=True) + 1e-12)
        text_embeddings = text_embeddings / (np.linalg.norm(text_embeddings, axis=1, keepdims=True) + 1e-12)
        logits = self.logit_scale * image_embeddings @ text_embeddings.T
        labels = np.arange(N)
        loss_i2t = float(-np.mean(np.log(self._softmax(logits)[np.arange(N), labels] + 1e-12)))
        loss_t2i = float(-np.mean(np.log(self._softmax(logits.T)[np.arange(N), labels] + 1e-12)))
        return (loss_i2t + loss_t2i) / 2.0

    def train_step(self, images: np.ndarray, texts: np.ndarray, lr: float = 0.001) -> Dict[str, Any]:
        image_emb = self._encode_visual(images)
        text_emb = self._encode_text(texts)
        loss = self._nt_xent_loss(image_emb, text_emb)
        self.loss_history.append(loss)
        N = len(images)
        image_emb_norm = image_emb / (np.linalg.norm(image_emb, axis=1, keepdims=True) + 1e-12)
        text_emb_norm = text_emb / (np.linalg.norm(text_emb, axis=1, keepdims=True) + 1e-12)
        logits = self.logit_scale * image_emb_norm @ text_emb_norm.T
        probs_i2t = self._softmax(logits)
        probs_t2i = self._softmax(logits.T)
        grad_i2t = probs_i2t
        grad_i2t[np.arange(N), np.arange(N)] -= 1
        grad_i2t /= N
        grad_t2i = probs_t2i
        grad_t2i[np.arange(N), np.arange(N)] -= 1
        grad_t2i /= N
        sim = image_emb_norm @ text_emb_norm.T
        grad_image = (grad_i2t @ text_emb_norm + grad_t2i.T @ image_emb_norm) * self.logit_scale
        grad_text = (grad_i2t.T @ image_emb_norm + grad_t2i @ text_emb_norm) * self.logit_scale
        h_i = self._relu(images @ self.visual_params['W1'] + self.visual_params['b1'])
        h_t = self._relu(texts @ self.text_params['W1'] + self.text_params['b1'])
        db2_i = np.sum(grad_image, axis=0)
        dw2_i = h_i.T @ grad_image
        dh_i = grad_image @ self.visual_params['W2'].T * (h_i > 0).astype(np.float64)
        db1_i = np.sum(dh_i, axis=0)
        dw1_i = images.T @ dh_i
        self.visual_params['W2'] -= lr * dw2_i
        self.visual_params['b2'] -= lr * db2_i
        self.visual_params['W1'] -= lr * dw1_i
        self.visual_params['b1'] -= lr * db1_i
        db2_t = np.sum(grad_text, axis=0)
        dw2_t = h_t.T @ grad_text
        dh_t = grad_text @ self.text_params['W2'].T * (h_t > 0).astype(np.float64)
        db1_t = np.sum(dh_t, axis=0)
        dw1_t = texts.T @ dh_t
        self.text_params['W2'] -= lr * dw2_t
        self.text_params['b2'] -= lr * db2_t
        self.text_params['W1'] -= lr * dw1_t
        self.text_params['b1'] -= lr * db1_t
        d_scale = float(np.sum(sim * (grad_i2t + grad_t2i.T)))
        self.logit_scale = np.array(max(0.01, min(100.0, self.logit_scale + lr * d_scale)), dtype=np.float64)
        return {'loss': loss, 'temperature': float(self.logit_scale)}

    def zero_shot_classify(self, image: np.ndarray, class_texts: List[np.ndarray]) -> int:
        image_emb = self._encode_visual(image)
        image_emb = image_emb / (np.linalg.norm(image_emb, axis=1, keepdims=True) + 1e-12)
        text_embs = np.array([self._encode_text(t.reshape(1, -1))[0] for t in class_texts])
        text_embs = text_embs / (np.linalg.norm(text_embs, axis=1, keepdims=True) + 1e-12)
        logits = self.logit_scale * image_emb @ text_embs.T
        return int(np.argmax(logits[0]))

    def get_report(self) -> Dict[str, Any]:
        return {
            'num_steps': len(self.loss_history),
            'last_loss': float(self.loss_history[-1]) if self.loss_history else None,
            'mean_loss': float(np.mean(self.loss_history[-10:])) if len(self.loss_history) >= 10 else (float(self.loss_history[-1]) if self.loss_history else None),
            'temperature': float(self.logit_scale),
            'embedding_dim': self.config.embedding_dim,
        }
