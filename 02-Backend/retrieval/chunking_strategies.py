
import re
import numpy as np
from dataclasses import dataclass
from typing import List, Callable, Optional


@dataclass
class Document:
    id: str
    text: str


def fixed_size_chunk(text: str, chunk_size: int = 100, overlap: int = 0) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def sentence_aware_chunk(text: str, max_chunk_size: int = 200) -> List[str]:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    chunks = []
    current = ''
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


def paragraph_aware_chunk(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs if paragraphs else [text]


def semantic_chunk(text: str, similarity_threshold: float = 0.5) -> List[str]:
    sentences = [s.strip() for s in text.replace('?', '.').replace('!', '.').split('.') if s.strip()]
    if len(sentences) <= 1:
        return [text]
    rng = np.random.RandomState(42)
    embeddings = rng.randn(len(sentences), 8)
    embeddings = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-10)
    chunks = []
    current = [sentences[0]]
    for i in range(1, len(sentences)):
        sim = float(embeddings[i-1] @ embeddings[i])
        if sim >= similarity_threshold:
            current.append(sentences[i])
        else:
            chunks.append(' '.join(current))
            current = [sentences[i]]
    if current:
        chunks.append(' '.join(current))
    return chunks


def hierarchical_chunk(text: str, levels: List[int] = None) -> dict:
    if levels is None:
        levels = [200, 500]
    chunks = {}
    for i, size in enumerate(levels):
        level_name = f"level_{i+1}"
        chunks[level_name] = fixed_size_chunk(text, chunk_size=size)
    return chunks


class Chunker:
    def __init__(self, strategy: str = 'fixed', chunk_size: int = 100, overlap: int = 0, max_chunk_size: int = 200, similarity_threshold: float = 0.5):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_chunk_size = max_chunk_size
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str) -> List[str]:
        if self.strategy == 'fixed':
            return fixed_size_chunk(text, self.chunk_size, self.overlap)
        elif self.strategy == 'sentence':
            return sentence_aware_chunk(text, self.max_chunk_size)
        elif self.strategy == 'paragraph':
            return paragraph_aware_chunk(text)
        elif self.strategy == 'semantic':
            return semantic_chunk(text, self.similarity_threshold)
        elif self.strategy == 'hierarchical':
            result = hierarchical_chunk(text)
            return result.get('level_1', [])
        return [text]
