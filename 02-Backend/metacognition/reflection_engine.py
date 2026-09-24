import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Reflection:
    key: str
    score: float
    feedback: str
    improvements: List[str]
    confidence: float


@dataclass
class ReflectionReport:
    reflections: List[Reflection]
    avg_score: float
    total_improvements: int
    strengths: List[str]
    weaknesses: List[str]


class ReflectionEngine:
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.reflections: Dict[str, List[Reflection]] = {}
        self.score_history: Dict[str, List[float]] = {}
        self.feedback_patterns: Dict[str, List[str]] = {}

    def record_feedback(self, key: str, feedback: str) -> None:
        if key not in self.feedback_patterns:
            self.feedback_patterns[key] = []
        self.feedback_patterns[key].append(feedback)

    def reflect(self, key: str, score: float, feedback: str) -> Reflection:
        improvements = self._identify_improvements(key, score)
        conf = self._reflection_confidence(key)
        reflection = Reflection(key=key, score=score, feedback=feedback, improvements=improvements, confidence=conf)
        if key not in self.reflections:
            self.reflections[key] = []
        self.reflections[key].append(reflection)
        if len(self.reflections[key]) > self.history_size:
            self.reflections[key] = self.reflections[key][-self.history_size:]
        if key not in self.score_history:
            self.score_history[key] = []
        self.score_history[key].append(score)
        if len(self.score_history[key]) > self.history_size:
            self.score_history[key] = self.score_history[key][-self.history_size:]
        return reflection

    def get_score_trend(self, key: str, window: int = 5) -> float:
        if key not in self.score_history or len(self.score_history[key]) < 2:
            return 0.0
        recent = self.score_history[key][-window:]
        if len(recent) < 2:
            return 0.0
        return (recent[-1] - recent[0]) / len(recent)

    def improvement_rate(self, key: str, window: int = 10) -> float:
        if key not in self.reflections or len(self.reflections[key]) < 2:
            return 0.0
        recent = self.reflections[key][-window:]
        if len(recent) < 2:
            return 0.0
        return (recent[-1].score - recent[0].score) / len(recent)

    def common_improvements(self, key: str, top_k: int = 5) -> List[str]:
        if key not in self.reflections:
            return []
        improvements: Dict[str, int] = {}
        for ref in self.reflections[key]:
            for imp in ref.improvements:
                improvements[imp] = improvements.get(imp, 0) + 1
        return sorted(improvements, key=improvements.get, reverse=True)[:top_k]

    def generate_report(self, key: str) -> ReflectionReport:
        refs = self.reflections.get(key, [])
        if not refs:
            return ReflectionReport(reflections=[], avg_score=0.0, total_improvements=0, strengths=[], weaknesses=[])
        scores = [r.score for r in refs]
        avg_score = sum(scores) / len(scores)
        all_improvements = [imp for r in refs for imp in r.improvements]
        improvements_by_key: Dict[str, int] = {}
        for imp in all_improvements:
            improvements_by_key[imp] = improvements_by_key.get(imp, 0) + 1
        common_imps = sorted(improvements_by_key, key=improvements_by_key.get, reverse=True)
        strengths = [imp for imp in common_imps if improvements_by_key[imp] >= 3][:5]
        weaknesses = [imp for imp in common_imps if improvements_by_key[imp] <= 2][:5]
        return ReflectionReport(reflections=refs, avg_score=avg_score, total_improvements=len(all_improvements), strengths=strengths, weaknesses=weaknesses)

    def _identify_improvements(self, key: str, score: float) -> List[str]:
        improvements = []
        if score < 0.3:
            improvements.append("Low performance")
        if score < 0.5:
            improvements.append("Needs practice")
        if score < 0.7:
            improvements.append("Inconsistent results")
        if score >= 0.7:
            improvements.append("Good job")
        if key in self.feedback_patterns:
            recent_feedback = self.feedback_patterns[key][-5:]
            feedback_text = " ".join(recent_feedback).lower()
            if "error" in feedback_text:
                improvements.append("Reduce errors")
            if "slow" in feedback_text:
                improvements.append("Increase speed")
            if "incomplete" in feedback_text:
                improvements.append("Improve completeness")
        return improvements

    def _reflection_confidence(self, key: str) -> float:
        if key not in self.score_history or len(self.score_history[key]) < 5:
            return 0.5
        recent = self.score_history[key][-10:]
        avg = sum(recent) / len(recent)
        variance = sum((s - avg) ** 2 for s in recent) / len(recent)
        return max(0.5, 1.0 - math.sqrt(variance))
