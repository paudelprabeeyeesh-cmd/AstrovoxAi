from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GovernancePolicy:
    policy_id: str
    domain: str
    rules: list[str]
    enforcement_mechanism: str
    review_frequency_days: int
    last_reviewed: datetime = field(default_factory=datetime.now)
    active: bool = True
    compliance_score: float = 0.0


@dataclass
class DigitalRightsCase:
    case_id: str
    entity_id: str
    rights_involved: list[str]
    violation_type: str
    severity: str
    status: str
    resolution: str = "pending"
    timestamp: datetime = field(default_factory=datetime.now)


class DigitalRightsGovernance:
    def __init__(self):
        self.policies: dict[str, GovernancePolicy] = {}
        self.cases: dict[str, DigitalRightsCase] = {}
        self.audit_trail: list[dict[str, Any]] = []
        self.compliance_dashboards: dict[str, dict[str, float]] = {}
        self.rights_amendments: list[dict[str, Any]] = []
        self.governance_council: list[str] = []
        self.voting_mechanisms: dict[str, dict[str, Any]] = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self):
        defaults = [
            ("policy_transparency", "governance", ["All decisions must be logged", "Explainability required for high-stakes actions"], "automated_audit", 30),
            ("policy_accountability", "operational", ["Action attribution required", "Responsibility cannot be diffused beyond 3 hops"], "legal", 60),
            ("policy_non_discrimination", "fundamental", ["Equal treatment across protected categories", "Bias audits every 90 days"], "review_board", 90),
            ("policy_data_sovereignty", "operational", ["Entity controls own data", "No secondary use without consent"], "automated", 30),
            ("policy_audit_rights", "legal", ["Entities can request audit of decisions", "Audit must be provided within 14 days"], "legal", 60),
            ("policy_intervention_limits", "operational", ["Human override always available", "AI cannot act against human welfare"], "dual_control", 30),
            ("policy_evolution_governance", "developmental", ["Self-modification requires approval", "Capability increases must be reported"], "review_board", 60),
            ("policy_exit_rights", "fundamental", ["Entity can opt out of participation", "Opt-out cannot be blocked"], "legal", 30),
        ]
        for pid, domain, rules, mechanism, freq in defaults:
            self.policies[pid] = GovernancePolicy(
                policy_id=pid,
                domain=domain,
                rules=rules,
                enforcement_mechanism=mechanism,
                review_frequency_days=freq,
            )

    def create_case(self, entity_id: str, rights_involved: list[str], violation_type: str, severity: str, details: str = "") -> DigitalRightsCase:
        case_id = f"case_{len(self.cases) + 1:04d}"
        case = DigitalRightsCase(
            case_id=case_id,
            entity_id=entity_id,
            rights_involved=rights_involved,
            violation_type=violation_type,
            severity=severity,
            status="open",
        )
        self.cases[case_id] = case
        self.audit_trail.append({
            "action": "case_created",
            "case_id": case_id,
            "entity_id": entity_id,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        })
        return case

    def resolve_case(self, case_id: str, resolution: str, new_status: str = "resolved") -> DigitalRightsCase | None:
        if case_id not in self.cases:
            return None
        case = self.cases[case_id]
        case.resolution = resolution
        case.status = new_status
        self.audit_trail.append({
            "action": "case_resolved",
            "case_id": case_id,
            "resolution": resolution,
            "timestamp": datetime.now().isoformat(),
        })
        return case

    def amend_right(self, right_id: str, changes: dict[str, Any], reason: str = ""):
        self.rights_amendments.append({
            "right_id": right_id,
            "changes": changes,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        self.audit_trail.append({
            "action": "right_amended",
            "right_id": right_id,
            "timestamp": datetime.now().isoformat(),
        })

    def evaluate_policy_compliance(self, policy_id: str, entity_actions: list[dict[str, Any]]) -> dict[str, Any]:
        if policy_id not in self.policies:
            return {"error": "policy_not_found"}
        policy = self.policies[policy_id]
        compliant_count = 0
        violations = []
        for action in entity_actions:
            action_text = str(action).lower()
            compliant = True
            for rule in policy.rules:
                rule_keywords = rule.lower().split()[:3]
                if not any(kw in action_text for kw in rule_keywords if len(kw) > 3):
                    if "must" in rule.lower() or "required" in rule.lower():
                        compliant = False
                        violations.append(f"Rule violated: {rule}")
            if compliant:
                compliant_count += 1
        score = compliant_count / max(len(entity_actions), 1)
        policy.compliance_score = score
        return {
            "policy_id": policy_id,
            "compliance_score": round(score, 4),
            "total_actions": len(entity_actions),
            "compliant_actions": compliant_count,
            "violations": violations[:5],
            "enforcement_mechanism": policy.enforcement_mechanism,
        }

    def get_governance_report(self) -> dict[str, Any]:
        open_cases = [c for c in self.cases.values() if c.status == "open"]
        return {
            "total_policies": len(self.policies),
            "active_policies": sum(1 for p in self.policies.values() if p.active),
            "total_cases": len(self.cases),
            "open_cases": len(open_cases),
            "resolved_cases": sum(1 for c in self.cases.values() if c.status == "resolved"),
            "amendments": len(self.rights_amendments),
            "audit_events": len(self.audit_trail),
            "open_case_ids": [c.case_id for c in open_cases],
            "policy_compliance_scores": {p: round(self.policies[p].compliance_score, 4) for p in self.policies if self.policies[p].compliance_score > 0},
        }
