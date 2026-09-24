from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import copy


@dataclass
class ImprovementIteration:
    iteration: int
    description: str
    complexity_before: float
    complexity_after: float
    quality_before: float
    quality_after: float
    applied: bool


@dataclass
class DesignSpec:
    name: str
    description: str
    complexity: float
    quality: float
    components: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


class RecursiveDesignImprover:
    def __init__(self, max_iterations: int = 50, quality_threshold: float = 0.9):
        self.max_iterations = int(max_iterations)
        self.quality_threshold = float(quality_threshold)
        self.improvement_history: List[ImprovementIteration] = []
        self.refactor_rules: List[str] = []
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self.refactor_rules = [
            "extract_common_patterns",
            "reduce_coupling",
            "increase_cohesion",
            "simplify_interfaces",
            "eliminate_duplication",
        ]

    def register_rule(self, rule: str) -> None:
        if rule not in self.refactor_rules:
            self.refactor_rules.append(rule)

    def improve(self, design: DesignSpec) -> DesignSpec:
        current = copy.deepcopy(design)
        self.improvement_history = []
        for i in range(self.max_iterations):
            iteration = self._apply_refactoring(i, current)
            self.improvement_history.append(iteration)
            if not iteration.applied:
                break
            current.complexity = iteration.complexity_after
            current.quality = iteration.quality_after
            if current.quality >= self.quality_threshold:
                break
        return current

    def _apply_refactoring(self, iteration: int, design: DesignSpec) -> ImprovementIteration:
        rule = self.refactor_rules[iteration % len(self.refactor_rules)]
        complexity_before = design.complexity
        quality_before = design.quality
        applied = False
        complexity_after = complexity_before
        quality_after = quality_before
        if rule == "extract_common_patterns" and len(design.components) > 3:
            extracted = len(design.components) // 3
            design.components = [f"CommonPattern_{i}" for i in range(extracted)] + design.components[extracted:]
            complexity_after = max(0.1, complexity_before * 0.85)
            quality_after = min(1.0, quality_before + 0.05)
            applied = True
        elif rule == "reduce_coupling" and len(design.constraints) > 1:
            design.constraints = design.constraints[: len(design.constraints) // 2]
            complexity_after = max(0.1, complexity_before * 0.9)
            quality_after = min(1.0, quality_before + 0.03)
            applied = True
        elif rule == "increase_cohesion":
            quality_after = min(1.0, quality_before + 0.04)
            complexity_after = max(0.1, complexity_before * 0.95)
            applied = True
        elif rule == "simplify_interfaces":
            complexity_after = max(0.1, complexity_before * 0.88)
            quality_after = min(1.0, quality_before + 0.02)
            applied = True
        elif rule == "eliminate_duplication":
            if len(design.components) > 2:
                unique = list(set(design.components))
                design.components = unique
                complexity_after = max(0.1, complexity_before * 0.8)
                quality_after = min(1.0, quality_before + 0.06)
                applied = True
        return ImprovementIteration(
            iteration=iteration,
            description=f"Applied {rule}",
            complexity_before=complexity_before,
            complexity_after=complexity_after,
            quality_before=quality_before,
            quality_after=quality_after,
            applied=applied,
        )

    def get_improvement_report(self) -> Dict[str, Any]:
        if not self.improvement_history:
            return {"status": "not_started"}
        applied = [i for i in self.improvement_history if i.applied]
        return {
            "total_iterations": len(self.improvement_history),
            "applied_count": len(applied),
            "final_complexity": self.improvement_history[-1].complexity_after,
            "final_quality": self.improvement_history[-1].quality_after,
            "total_complexity_reduction": self.improvement_history[0].complexity_before - self.improvement_history[-1].complexity_after,
            "total_quality_gain": self.improvement_history[-1].quality_after - self.improvement_history[0].quality_before,
        }

    def measure_convergence(self) -> float:
        if len(self.improvement_history) < 2:
            return 0.0
        recent = self.improvement_history[-5:]
        quality_deltas = [recent[i].quality_after - recent[i - 1].quality_after for i in range(1, len(recent))]
        return float(sum(abs(d) for d in quality_deltas) / len(quality_deltas))
