import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InstructionExample:
    instruction: str
    input_data: Optional[str]
    expected_output: str


class InstructionFollowingModel:
    def __init__(self, vocab_size: int, instruction_dim: int, hidden_dim: int):
        self.vocab_size = vocab_size
        self.instruction_dim = instruction_dim
        self.hidden_dim = hidden_dim
        self.W_inst_enc = np.random.randn(instruction_dim, hidden_dim) * 0.02
        self.W_ffn = np.random.randn(hidden_dim, hidden_dim) * 0.02
        self.W_out = np.random.randn(hidden_dim, vocab_size) * 0.02
        self.b_ffn = np.zeros(hidden_dim)

    def encode_instruction(self, instruction_vector: np.ndarray) -> np.ndarray:
        return np.tanh(instruction_vector @ self.W_inst_enc)

    def forward(self, instruction_encoding: np.ndarray) -> np.ndarray:
        hidden = np.tanh(instruction_encoding @ self.W_ffn + self.b_ffn)
        return hidden @ self.W_out

    def follow_instruction(self, instruction_vector: np.ndarray, top_k: int = 1) -> Tuple[np.ndarray, float]:
        encoding = self.encode_instruction(instruction_vector)
        logits = self.forward(encoding)
        probs = np.exp(logits - np.max(logits))
        probs = probs / (np.sum(probs) + 1e-8)
        confidence = float(np.max(probs))
        if top_k == 1:
            token = int(np.argmax(probs))
            return np.array([token]), confidence
        top_indices = np.argsort(probs)[-top_k:]
        return top_indices, confidence

    def instruction_consistency(self, instruction_vector: np.ndarray, num_samples: int = 5) -> float:
        outputs = [self.follow_instruction(instruction_vector)[0][0] for _ in range(num_samples)]
        return float(np.mean([o == outputs[0] for o in outputs]))


class InstructionTuningAnalyzer:
    def __init__(self):
        self.loss_before_tuning: List[float] = []
        self.loss_after_tuning: List[float] = []
        self.instruction_types: List[str] = []

    def record_pre_tuning_loss(self, loss: float, instruction_type: str):
        self.loss_before_tuning.append(loss)
        self.instruction_types.append(instruction_type)

    def record_post_tuning_loss(self, loss: float):
        self.loss_after_tuning.append(loss)

    def improvement_by_type(self) -> Dict[str, float]:
        improvements: Dict[str, List[float]] = {}
        for i, itype in enumerate(self.instruction_types):
            if i < len(self.loss_after_tuning):
                improvements.setdefault(itype, []).append(self.loss_before_tuning[i] - self.loss_after_tuning[i])
        return {k: float(np.mean(v)) for k, v in improvements.items()}

    def overall_improvement(self) -> float:
        if not self.loss_before_tuning or not self.loss_after_tuning:
            return 0.0
        return float(np.mean(np.array(self.loss_before_tuning) - np.array(self.loss_after_tuning)))


class GeneralizationGapAnalyzer:
    def __init__(self):
        self.train_performances: List[float] = []
        self.test_performances: List[float] = []

    def record(self, train_perf: float, test_perf: float):
        self.train_performances.append(train_perf)
        self.test_performances.append(test_perf)

    def compute_gap(self) -> float:
        if not self.train_performances:
            return 0.0
        return float(np.mean(np.array(self.train_performances) - np.array(self.test_performances)))
