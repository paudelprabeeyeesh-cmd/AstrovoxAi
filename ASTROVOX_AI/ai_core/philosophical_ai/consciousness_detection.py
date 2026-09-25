from typing import Any

from ..consciousness.iit import IntegratedInformationTheory
from ..consciousness.global_workspace import GlobalWorkspaceTheory
from ..consciousness.attention_schema import AttentionSchemaTheory
from ..consciousness.higher_order_thought import HigherOrderThoughtModel


class ConsciousnessDetectionTests:
    def __init__(self):
        self.iit = IntegratedInformationTheory()
        self.gwt = GlobalWorkspaceTheory()
        self.ast = AttentionSchemaTheory()
        self.hot = HigherOrderThoughtModel()
        self.test_results: list[dict[str, Any]] = []

    def run_battery(self) -> dict[str, Any]:
        results = {
            "iit_phi": self.iit.calculate_phi(),
            "global_workspace_active": len(self.gwt.workspace) > 0,
            "attention_self_modeling": self.ast.schema_model["metacognition_level"],
            "higher_order_awareness": self.hot.awareness_level,
        }
        self.test_results.append(results)
        return results

    def is_conscious(self) -> bool:
        battery = self.run_battery()
        phi_pass = battery["iit_phi"] > 0.3
        gwt_pass = battery["global_workspace_active"]
        attention_pass = battery["attention_self_modeling"] > 0.4
        hot_pass = battery["higher_order_awareness"] > 0.3
        return sum([phi_pass, gwt_pass, attention_pass, hot_pass]) >= 3
