import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import random


@dataclass
class CreativeOutput:
    content: Any
    novelty: float
    quality: float
    style_vector: Optional[np.ndarray] = None


class DivergentGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._generation_count = 0

    def generate(self, prompt: str, n_variants: int = 5, temperature: float = 1.0) -> List[CreativeOutput]:
        random.seed(self.seed + self._generation_count)
        outputs = []
        for i in range(n_variants):
            noise = np.random.randn(16) * temperature
            content = f"{prompt}_variant_{i}_n{np.linalg.norm(noise):.2f}"
            novelty = float(np.linalg.norm(noise))
            quality = float(np.random.beta(2, 5))
            outputs.append(CreativeOutput(
                content=content,
                novelty=novelty,
                quality=quality,
                style_vector=noise,
            ))
        self._generation_count += 1
        return outputs

    def recombine(self, outputs: List[CreativeOutput]) -> List[CreativeOutput]:
        if len(outputs) < 2:
            return outputs
        children = []
        for i in range(0, len(outputs) - 1, 2):
            parent_a, parent_b = outputs[i], outputs[i + 1]
            child_style = 0.5 * (parent_a.style_vector + parent_b.style_vector)
            child_style += np.random.randn(16) * 0.1
            child_content = f"recomb_{parent_a.content}_{parent_b.content}"
            novelty = float(np.linalg.norm(child_style))
            quality = float(np.clip(0.5 * (parent_a.quality + parent_b.quality) + 0.1, 0, 1))
            children.append(CreativeOutput(
                content=child_content,
                novelty=novelty,
                quality=quality,
                style_vector=child_style,
            ))
        return children


class NoveltySearch:
    def __init__(self, archive_size: int = 100):
        self.archive_size = archive_size
        self.archive: List[Tuple[np.ndarray, float]] = []

    def evaluate_novelty(self, behavior: np.ndarray) -> float:
        if not self.archive:
            return 1.0
        distances = [np.linalg.norm(behavior - b) for b, _ in self.archive]
        k = min(15, len(distances))
        nearest = sorted(distances)[:k]
        return float(np.mean(nearest))

    def update_archive(self, behavior: np.ndarray, fitness: float) -> None:
        novelty = self.evaluate_novelty(behavior)
        self.archive.append((behavior, novelty))
        if len(self.archive) > self.archive_size:
            self.archive.sort(key=lambda x: x[1])
            self.archive = self.archive[-self.archive_size:]

    def select(self, candidates: List[Tuple[np.ndarray, float]], top_k: int = 5) -> List[int]:
        scores = [(i, self.evaluate_novelty(b)) for i, (b, _) in enumerate(candidates)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, _ in scores[:top_k]]


class StyleTransferEngine:
    def __init__(self, style_dim: int = 16):
        self.style_dim = style_dim
        self.styles: Dict[str, np.ndarray] = {}

    def register_style(self, name: str, vector: Optional[np.ndarray] = None) -> None:
        if vector is None:
            vector = np.random.randn(self.style_dim)
        self.styles[name] = vector

    def transfer(self, content_vector: np.ndarray, style_name: str, strength: float = 0.5) -> np.ndarray:
        if style_name not in self.styles:
            raise KeyError(f"Unknown style: {style_name}")
        style_vec = self.styles[style_name]
        return (1 - strength) * content_vector + strength * style_vec

    def blend_styles(self, style_names: List[str], weights: Optional[List[float]] = None) -> np.ndarray:
        if not self.styles:
            return np.zeros(self.style_dim)
        if weights is None:
            weights = [1.0 / len(style_names)] * len(style_names)
        blended = np.zeros(self.style_dim)
        for name, w in zip(style_names, weights):
            if name in self.styles:
                blended += w * self.styles[name]
        return blended


class CreativityEngine:
    def __init__(self):
        self.divergent = DivergentGenerator()
        self.novelty = NoveltySearch()
        self.style = StyleTransferEngine()
        self._output_log: List[Dict[str, Any]] = []

    def generate(self, prompt: str, n: int = 5, temperature: float = 1.0) -> List[CreativeOutput]:
        outputs = self.divergent.generate(prompt, n_variants=n, temperature=temperature)
        for out in outputs:
            self._output_log.append({
                "prompt": prompt,
                "content": out.content,
                "novelty": out.novelty,
                "quality": out.quality,
            })
            if out.style_vector is not None:
                self.novelty.update_archive(out.style_vector, out.quality)
        return outputs

    def recombine(self, outputs: List[CreativeOutput]) -> List[CreativeOutput]:
        return self.divergent.recombine(outputs)

    def transfer_style(self, content_vector: np.ndarray, style_name: str, strength: float = 0.5) -> np.ndarray:
        return self.style.transfer(content_vector, style_name, strength=strength)

    def get_output_log(self) -> List[Dict[str, Any]]:
        return list(self._output_log)
