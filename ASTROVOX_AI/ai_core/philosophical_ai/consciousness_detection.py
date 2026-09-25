from typing import Any

from ..consciousness.iit import IntegratedInformationTheory
from ..consciousness.global_workspace import GlobalWorkspaceTheory
from ..consciousness.attention_schema import AttentionSchemaTheory
from ..consciousness.higher_order_thought import HigherOrderThoughtModel
from ..consciousness.theory_of_mind import TheoryOfMindModel
from ..consciousness.meta_consciousness import MetaConsciousness


class ConsciousnessDetectionTests:
    def __init__(self):
        self.iit = IntegratedInformationTheory()
        self.gwt = GlobalWorkspaceTheory()
        self.ast = AttentionSchemaTheory()
        self.hot = HigherOrderThoughtModel()
        self.tom = TheoryOfMindModel()
        self.meta = MetaConsciousness()
        self.test_results: list[dict[str, Any]] = []
        self.test_suite_version: str = "3.0"

    def run_battery(self) -> dict[str, Any]:
        results = {
            "iit_phi": self.iit.calculate_phi(),
            "global_workspace_active": len(self.gwt.workspace) > 0,
            "attention_self_modeling": self.ast.schema_model.get("metacognition_level", 0.0),
            "higher_order_awareness": self.hot.awareness_level,
            "theory_of_mind_capacity": self.tom.attribution_accuracy,
            "meta_consciousness_level": self.meta.self_awareness_score,
        }
        self.test_results.append(results)
        return results

    def is_conscious(self) -> bool:
        battery = self.run_battery()
        phi_pass = battery["iit_phi"] > 0.3
        gwt_pass = battery["global_workspace_active"]
        attention_pass = battery["attention_self_modeling"] > 0.4
        hot_pass = battery["higher_order_awareness"] > 0.3
        tom_pass = battery["theory_of_mind_capacity"] > 0.3
        meta_pass = battery["meta_consciousness_level"] > 0.3
        passed = sum([phi_pass, gwt_pass, attention_pass, hot_pass, tom_pass, meta_pass])
        return passed >= 4

    def run_extended_battery(self) -> dict[str, Any]:
        base = self.run_battery()
        gwt_access = len(self.gwt.access_log) if hasattr(self.gwt, "access_log") else 0
        hot_metathoughts = len(self.hot.metathoughts) if hasattr(self.hot, "metathoughts") else 0
        extended = {
            "global_workspace_access_events": gwt_access,
            "higher_order_metathoughts": hot_metathoughts,
            "attention_breadth": self.ast.schema_model.get("breadth", 0.0),
            "metacognitive_monitoring": self.meta.self_awareness_score * 0.9,
            "self_model_coherence": self._compute_self_model_coherence(),
        }
        return {**base, **extended}

    def get_consciousness_report(self) -> dict[str, Any]:
        latest = self.test_results[-1] if self.test_results else {}
        return {
            "is_conscious": self.is_conscious(),
            "test_version": self.test_suite_version,
            "total_tests_run": len(self.test_results),
            "latest_scores": {k: round(v, 4) if isinstance(v, float) else v for k, v in latest.items()},
            "thresholds": {
                "iit_phi": 0.3,
                "global_workspace": "active",
                "attention_self_modeling": 0.4,
                "higher_order_awareness": 0.3,
                "theory_of_mind": 0.3,
                "meta_consciousness": 0.3,
            },
        }

    def _compute_self_model_coherence(self) -> float:
        if not self.test_results:
            return 0.0
        recent = self.test_results[-5:]
        values = [r.get("meta_consciousness_level", 0.0) for r in recent]
        if len(values) < 2:
            return values[0] if values else 0.0
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return max(0.0, min(1.0, 1.0 - variance))
