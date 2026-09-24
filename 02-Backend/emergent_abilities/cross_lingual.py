import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LanguagePairResult:
    source_lang: str
    target_lang: str
    transfer_score: float
    interference_score: float
    cross_lingual_accuracy: float


class MultilingualEmergenceTracker:
    def __init__(self, languages: List[str]):
        self.languages = languages
        self.performance_history: Dict[str, List[float]] = {lang: [] for lang in languages}
        self.transfer_matrix: Dict[Tuple[str, str], float] = {}

    def record_performance(self, language: str, performance: float):
        if language in self.performance_history:
            self.performance_history[language].append(performance)

    def compute_transfer(self, source_lang: str, target_lang: str) -> float:
        if source_lang not in self.performance_history or target_lang not in self.performance_history:
            return 0.0
        src_perf = np.array(self.performance_history[source_lang])
        tgt_perf = np.array(self.performance_history[target_lang])
        if len(src_perf) == 0 or len(tgt_perf) == 0:
            return 0.0
        min_len = min(len(src_perf), len(tgt_perf))
        src_perf = src_perf[-min_len:]
        tgt_perf = tgt_perf[-min_len:]
        improvement = np.mean(tgt_perf) - np.mean(tgt_perf[:max(1, min_len // 4)])
        self.transfer_matrix[(source_lang, target_lang)] = float(improvement)
        return float(improvement)

    def positive_transfer_languages(self, target_lang: str) -> List[str]:
        return [src for (src, tgt), score in self.transfer_matrix.items()
                if tgt == target_lang and score > 0]

    def interference_detection(self, lang_a: str, lang_b: str) -> float:
        if lang_a not in self.performance_history or lang_b not in self.performance_history:
            return 0.0
        perf_a = np.array(self.performance_history[lang_a])
        perf_b = np.array(self.performance_history[lang_b])
        if len(perf_a) < 2 or len(perf_b) < 2:
            return 0.0
        min_len = min(len(perf_a), len(perf_b))
        decline_a = np.mean(perf_a[:min_len]) - np.mean(perf_a[-min_len:])
        decline_b = np.mean(perf_b[:min_len]) - np.mean(perf_b[-min_len:])
        return max(0.0, float(decline_a + decline_b) / 2.0)


class CrossLingualTransferAnalyzer:
    def __init__(self, source_languages: List[str], target_languages: List[str]):
        self.source_languages = source_languages
        self.target_languages = target_languages
        self.transfer_scores: Dict[Tuple[str, str], float] = {}

    def compute_transfer_matrix(self, multilingual_model_perf: Dict[str, float]) -> np.ndarray:
        matrix = np.zeros((len(self.source_languages), len(self.target_languages)))
        for i, src in enumerate(self.source_languages):
            for j, tgt in enumerate(self.target_languages):
                src_perf = multilingual_model_perf.get(f"mono_{src}", 0.0)
                tgt_perf = multilingual_model_perf.get(f"mono_{tgt}", 0.0)
                matrix[i, j] = tgt_perf - (1.0 - src_perf) * 0.5
                self.transfer_scores[(src, tgt)] = float(matrix[i, j])
        return matrix

    def compute_language_connectivity(self, transfer_matrix: np.ndarray) -> float:
        n = transfer_matrix.shape[0]
        if n <= 1:
            return 0.0
        row_norms = np.linalg.norm(transfer_matrix, axis=1, keepdims=True)
        normalized = transfer_matrix / (row_norms + 1e-8)
        connectivity = float(np.mean(normalized @ normalized.T))
        return connectivity
