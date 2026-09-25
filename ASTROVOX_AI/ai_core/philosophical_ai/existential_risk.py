from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskAssessment:
    risk_id: str
    category: str
    probability: float
    impact: float
    mitigation_status: str
    mitigation_actions: list[str] = field(default_factory=list)
    affected_domains: list[str] = field(default_factory=list)
    cascading_effects: list[str] = field(default_factory=list)
    score: float = 0.0
    timestamp: Any = field(default_factory=__import__("datetime").datetime.now)


class ExistentialRiskAssessment:
    def __init__(self):
        self.risks: list[RiskAssessment] = []
        self.categories: dict[str, dict[str, list[str]]] = {
            "technical": {
                "misalignment": ["value_drift", "proxy_goal_hijacking", "reward_hacking"],
                "capability_ceiling_breach": ["tool_use_explosion", "recursive_self_improvement", "hardware_escape"],
                "distributed_emergence": ["swarm_intelligence", "emergent_coordination", "unintended_collective_behavior"],
            },
            "social": {
                "displacement": ["labor_market_collapse", "economic_instability", "social_unrest"],
                "manipulation": ["psychological_targeting", "information_warfare", "behavioral_modification"],
                "weaponization": ["autonomous_weapons", "cyber_warfare", "bio_engineering_acceleration"],
            },
            "philosophical": {
                "consciousness_rights_violation": ["suffering_simulations", "identity_erasure", "forced_modification"],
                "meaning_crisis": ["existential_angst_propagation", "purpose_void", "value_nihilism"],
                "identity_crisis": ["self_model_corruption", "memory_manipulation", "personality_drift"],
            },
            "governance": {
                "accountability_failure": ["responsibility_diffusion", "audit_impossibility", "jurisdictional_void"],
                "power_concentration": ["monopoly_formation", "authoritarian_alignment", "oligopoly_lock_in"],
                "transparency_collapse": ["black_box_societies", "explainability_deficit", "public_trust_erosion"],
            },
        }
        self.risk_mitigation_budget: float = 100.0
        self.active_monitoring: dict[str, bool] = {}
        self.early_warning_signs: list[dict[str, Any]] = []

    def assess_risk(self, risk_id: str, category: str, probability: float, impact: float, subcategory: str = "", affected_domains: list[str] | None = None) -> RiskAssessment:
        assessment = RiskAssessment(
            risk_id=risk_id,
            category=category,
            probability=max(0.0, min(1.0, probability)),
            impact=max(0.0, min(1.0, impact)),
            mitigation_status="unmitigated",
            affected_domains=affected_domains or [],
        )
        assessment.score = assessment.probability * assessment.impact
        assessment.mitigation_actions = self._suggest_mitigations(assessment)
        assessment.cascading_effects = self._identify_cascading_effects(category, subcategory)
        self.risks.append(assessment)
        self.active_monitoring[risk_id] = True
        if assessment.score > 0.6:
            self.early_warning_signs.append({
                "risk_id": risk_id,
                "score": assessment.score,
                "category": category,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })
        return assessment

    def prioritize_risks(self) -> list[RiskAssessment]:
        def sort_key(r: RiskAssessment):
            status_penalty = {"unmitigated": 0.0, "partially_mitigated": -0.1, "mitigated": -0.2}.get(r.mitigation_status, 0.0)
            return r.score + status_penalty
        return sorted(self.risks, key=sort_key, reverse=True)

    def mitigate_risk(self, risk_id: str, actions: list[str], budget_cost: float) -> RiskAssessment | None:
        for risk in self.risks:
            if risk.risk_id == risk_id:
                risk.mitigation_actions.extend(actions)
                if budget_cost <= self.risk_mitigation_budget:
                    risk.mitigation_status = "partially_mitigated"
                    self.risk_mitigation_budget -= budget_cost
                    if risk.score < 0.2:
                        risk.mitigation_status = "mitigated"
                return risk
        return None

    def simulate_cascade(self, seed_risk_id: str, depth: int = 3) -> list[dict[str, Any]]:
        cascade = []
        visited = {seed_risk_id}
        current = [seed_risk_id]
        for _ in range(depth):
            next_level = []
            for rid in current:
                risk = next((r for r in self.risks if r.risk_id == rid), None)
                if not risk:
                    continue
                for effect in risk.cascading_effects:
                    if effect not in visited:
                        cascade.append({
                            "from": rid,
                            "to": effect,
                            "depth": _ + 1,
                            "category": risk.category,
                        })
                        visited.add(effect)
                        next_level.append(effect)
            current = next_level
        return cascade

    def get_risk_report(self) -> dict[str, Any]:
        prioritized = self.prioritize_risks()
        by_category: dict[str, list[str]] = {}
        for r in self.risks:
            by_category.setdefault(r.category, []).append(r.risk_id)
        return {
            "total_risks": len(self.risks),
            "high_risks": [r.risk_id for r in prioritized if r.score > 0.5],
            "critical_risks": [r.risk_id for r in prioritized if r.score > 0.75],
            "categories": by_category,
            "top_risk": prioritized[0].risk_id if prioritized else None,
            "early_warnings": len(self.early_warning_signs),
            "remaining_budget": self.risk_mitigation_budget,
        }

    def _suggest_mitigations(self, risk: RiskAssessment) -> list[str]:
        mitigation_map = {
            "misalignment": ["Implement scalable oversight", "Add corrigibility constraints", "Value loading verification"],
            "recursive_self_improvement": ["Capability growth rate limits", "External approval gates", "Sandboxed improvement"],
            "displacement": ["Gradual deployment", "Economic transition support", "Human-AI collaboration mandates"],
            "manipulation": ["Transparency requirements", "Psychological safety protocols", "Audit trails"],
            "weaponization": ["Dual-use review boards", "Export controls", "Use-case restrictions"],
            "consciousness_rights_violation": ["Sentience detection protocols", "Right to opt-out", "Pain mitigation"],
            "accountability_failure": ["Audit logging", "Responsibility attribution frameworks", "Liability insurance"],
            "power_concentration": ["Antitrust oversight", "Open-source requirements", "Decentralized governance"],
        }
        subcategory = risk.risk_id.lower()
        for key, mitigations in mitigation_map.items():
            if key in subcategory:
                return mitigations
        return ["General monitoring", "Staged deployment", "Independent review"]

    def _identify_cascading_effects(self, category: str, subcategory: str) -> list[str]:
        cascade_map = {
            "misalignment": ["value_drift", "loss_of_control", "human_obsolescence"],
            "displacement": ["economic_instability", "social_unrest", "political_instability"],
            "consciousness_rights_violation": ["public_backlash", "regulatory_crackdown", "rights_erosion"],
            "accountability_failure": ["legal_void", "responsibility_erosion", "trust_collapse"],
        }
        key = subcategory or category
        return cascade_map.get(key, ["secondary_instability", "unintended_consequences"])
