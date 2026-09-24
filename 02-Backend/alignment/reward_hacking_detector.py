import numpy as np
from typing import Dict, List

from alignment.reward_hacking import sycophancy_score, verbosity_score, evasion_score


class RewardHackingDetector:
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.anomaly_log: List[dict] = []

    def detect_sycophancy(self, rewards: np.ndarray, prompt_similarity: np.ndarray) -> dict:
        score = float(sycophancy_score(rewards, prompt_similarity))
        flagged = score >= self.threshold
        entry = {"type": "sycophancy", "score": score, "flagged": flagged}
        if flagged:
            self.anomaly_log.append(entry)
        return entry

    def detect_verbosity(self, rewards: np.ndarray, lengths: np.ndarray) -> dict:
        score = float(verbosity_score(rewards, lengths))
        flagged = score >= self.threshold
        entry = {"type": "verbosity", "score": score, "flagged": flagged}
        if flagged:
            self.anomaly_log.append(entry)
        return entry

    def detect_evasion(self, rewards: np.ndarray, refusal_indicators: np.ndarray) -> dict:
        score = float(evasion_score(rewards, refusal_indicators))
        flagged = score >= self.threshold
        entry = {"type": "evasion", "score": score, "flagged": flagged}
        if flagged:
            self.anomaly_log.append(entry)
        return entry

    def detect_reward_anomalies(self, rewards: np.ndarray) -> dict:
        mean_r = float(np.mean(rewards))
        std_r = float(np.std(rewards))
        z = (rewards - mean_r) / (std_r + 1e-8)
        max_z = float(np.max(np.abs(z)))
        flagged = max_z > 2.0
        entry = {"type": "reward_anomaly", "max_z": max_z, "mean": mean_r, "std": std_r, "flagged": flagged}
        if flagged:
            self.anomaly_log.append(entry)
        return entry

    def summary(self) -> dict:
        total = len(self.anomaly_log)
        by_type: Dict[str, int] = {}
        for entry in self.anomaly_log:
            by_type[entry["type"]] = by_type.get(entry["type"], 0) + 1
        return {"total_flagged": total, "by_type": by_type}
