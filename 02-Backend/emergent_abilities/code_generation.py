import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CodeGenerationResult:
    generated_code: str
    tokens: List[int]
    syntax_valid: bool
    semantic_score: float
    passes_tests: bool


class CodeEmergenceModel:
    def __init__(self, vocab_size: int, hidden_dim: int, max_length: int = 256):
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.max_length = max_length
        self.W_embed = np.random.randn(vocab_size, hidden_dim) * 0.02
        self.W_transformer = np.random.randn(hidden_dim, hidden_dim) * 0.02
        self.W_out = np.random.randn(hidden_dim, vocab_size) * 0.02

    def tokenize(self, code: str) -> List[int]:
        return [hash(ch) % self.vocab_size for ch in code]

    def detokenize(self, tokens: List[int]) -> str:
        return "".join(chr(t % 128) for t in tokens)

    def check_syntax(self, tokens: List[int]) -> bool:
        return len(tokens) > 0 and tokens[0] % 2 == 0

    def check_semantic_validity(self, tokens: List[int]) -> float:
        if not tokens:
            return 0.0
        unique_ratio = len(set(tokens)) / max(len(tokens), 1)
        balance = 1.0 - abs(len(tokens) - 10) / 20.0
        return min(1.0, unique_ratio * balance)

    def generate(self, prompt: str, max_new_tokens: int = 32) -> CodeGenerationResult:
        prompt_tokens = self.tokenize(prompt)
        hidden = np.mean([self.W_embed[t] for t in prompt_tokens], axis=0) if prompt_tokens else np.zeros(self.hidden_dim)
        generated_tokens = list(prompt_tokens)
        for _ in range(max_new_tokens):
            hidden = np.tanh(hidden @ self.W_transformer)
            logits = hidden @ self.W_out
            next_token = int(np.argmax(logits))
            generated_tokens.append(next_token)
            hidden = self.W_embed[next_token]
        code = self.detokenize(generated_tokens)
        syntax_valid = self.check_syntax(generated_tokens)
        semantic_score = self.check_semantic_validity(generated_tokens)
        return CodeGenerationResult(generated_code=code, tokens=generated_tokens, syntax_valid=syntax_valid,
                                    semantic_score=semantic_score, passes_tests=syntax_valid and semantic_score > 0.5)


class ProgramSynthesisAnalyzer:
    def __init__(self):
        self.synthesis_results: List[CodeGenerationResult] = []
        self.task_complexity_scores: Dict[str, float] = {}

    def record_synthesis(self, result: CodeGenerationResult, task_complexity: float):
        self.synthesis_results.append(result)
        self.task_complexity_scores[result.generated_code] = task_complexity

    def emergence_threshold(self) -> float:
        if len(self.synthesis_results) < 5:
            return 0.0
        pass_rates = [1.0 if r.passes_tests else 0.0 for r in self.synthesis_results]
        model_sizes = np.linspace(1e8, 1e11, len(pass_rates))
        sorted_idx = np.argsort(model_sizes)
        pass_rates_arr = np.array(pass_rates)[sorted_idx]
        diffs = np.diff(pass_rates_arr)
        threshold_idx = int(np.argmax(diffs)) if np.max(diffs) > 0 else 0
        return float(model_sizes[sorted_idx[threshold_idx]])

    def code_quality_trend(self) -> np.ndarray:
        return np.array([r.semantic_score for r in self.synthesis_results])
