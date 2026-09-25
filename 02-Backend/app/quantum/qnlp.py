import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from .circuit_simulator import QuantumCircuitSimulator
import re

@dataclass
class QuantumWordEmbedding:
    word: str
    amplitude: np.ndarray
    dimension: int

class QuantumNLP:
    def __init__(self, vocab_size: int = 1000, embedding_dim: int = 4):
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.vocab: Dict[str, int] = {}
        self.embeddings: Dict[str, QuantumWordEmbedding] = {}
        self._next_id = 0

    def _encode_word(self, word: str) -> np.ndarray:
        if word not in self.vocab:
            self.vocab[word] = self._next_id
            self._next_id += 1
        word_id = self.vocab[word]
        amplitudes = np.zeros(self.embedding_dim, dtype=np.float64)
        for i in range(self.embedding_dim):
            bit = (word_id >> i) & 1
            amplitudes[i] = bit * np.pi / self.embedding_dim
        return amplitudes

    def embed_word(self, word: str) -> QuantumWordEmbedding:
        if word not in self.embeddings:
            amp = self._encode_word(word)
            self.embeddings[word] = QuantumWordEmbedding(word=word, amplitude=amp, dimension=self.embedding_dim)
        return self.embeddings[word]

    def encode_sentence(self, sentence: str) -> QuantumCircuitSimulator:
        words = re.findall(r"\w+", sentence.lower())
        n_qubits = max(self.embedding_dim, len(words))
        sim = QuantumCircuitSimulator(n_qubits)
        for i, word in enumerate(words):
            if i >= n_qubits:
                break
            embedding = self.embed_word(word)
            for j, val in enumerate(embedding.amplitude):
                if j < n_qubits:
                    sim.ry(j, val)
            if i < n_qubits - 1:
                sim.cnot(i, i + 1)
        return sim

    def similarity(self, sentence1: str, sentence2: str) -> float:
        sim1 = self.encode_sentence(sentence1)
        sim2 = self.encode_sentence(sentence2)
        sv1 = sim1.get_statevector()
        sv2 = sim2.get_statevector()
        min_dim = min(len(sv1), len(sv2))
        sv1_pad = np.zeros(min_dim, dtype=np.complex128)
        sv2_pad = np.zeros(min_dim, dtype=np.complex128)
        sv1_pad[:min(len(sv1), min_dim)] = sv1[:min(len(sv1), min_dim)]
        sv2_pad[:min(len(sv2), min_dim)] = sv2[:min(len(sv2), min_dim)]
        fidelity = float(np.abs(np.dot(sv1_pad, np.conj(sv2_pad))) ** 2)
        return fidelity

    def quantum_sentiment(self, sentence: str) -> Dict[str, float]:
        sim = self.encode_sentence(sentence)
        probs = sim.get_probabilities()
        positive = sum(p for k, p in probs.items() if k.count("1") <= len(k) // 2)
        negative = sum(p for k, p in probs.items() if k.count("1") > len(k) // 2)
        return {"positive": positive, "negative": negative, "neutral": 1.0 - positive - negative}

    def quantum_ner(self, sentence: str) -> List[Tuple[str, str, float]]:
        words = re.findall(r"\w+", sentence)
        entities = []
        sim = self.encode_sentence(sentence)
        probs = sim.get_probabilities()
        sorted_states = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        for i, (state, prob) in enumerate(sorted_states[:len(words)]):
            entity_type = "PERSON" if state.count("1") % 3 == 0 else "ORG" if state.count("1") % 3 == 1 else "LOC"
            entities.append((words[i] if i < len(words) else state, entity_type, prob))
        return entities

    def quantum_text_classification(self, text: str, categories: List[str]) -> Tuple[str, float]:
        sim = self.encode_sentence(text)
        probs = sim.get_probabilities()
        scores = {}
        for i, cat in enumerate(categories):
            state_key = format(i, f"0{max(3, sim.num_qubits)}b")
            scores[cat] = probs.get(state_key, 0.0)
        best_cat = max(scores, key=scores.get)
        return best_cat, scores[best_cat]

    def quantum_summarization_score(self, sentence: str) -> float:
        sim = self.encode_sentence(sentence)
        probs = sim.get_probabilities()
        entropy = -sum(p * np.log2(p + 1e-10) for p in probs.values())
        max_entropy = np.log2(len(probs))
        return float(1.0 - entropy / max_entropy) if max_entropy > 0 else 0.0

    def build_vocab(self, sentences: List[str]) -> None:
        for sentence in sentences:
            words = re.findall(r"\w+", sentence.lower())
            for word in words:
                if word not in self.vocab:
                    self.vocab[word] = self._next_id
                    self._next_id += 1

    def get_embedding_matrix(self) -> np.ndarray:
        matrix = np.zeros((len(self.vocab), self.embedding_dim))
        for word, idx in self.vocab.items():
            if word in self.embeddings:
                matrix[idx] = self.embeddings[word].amplitude
        return matrix
