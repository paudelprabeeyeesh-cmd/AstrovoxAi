"""Governance policies and review checklist."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PolicyItem:
    id: str
    title: str
    description: str
    category: str
    mandatory: bool
    owner: str
    last_reviewed: Optional[float] = None
    next_review: Optional[float] = None


@dataclass
class ChecklistItem:
    id: str
    description: str
    category: str
    required: bool
    passed: bool = False
    evidence: str = ""
    reviewer: str = ""
    reviewed_at: Optional[float] = None


@dataclass
class ReviewChecklist:
    id: str
    name: str
    items: list[ChecklistItem]
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class GovernancePolicy:
    """Manage governance policies for AI systems."""

    DEFAULT_POLICIES = [
        PolicyItem(
            id="pol-1",
            title="Prompt Injection Testing",
            description="All model releases must pass prompt injection testing",
            category="security",
            mandatory=True,
            owner="Security Team",
        ),
        PolicyItem(
            id="pol-2",
            title="Jailbreak Testing",
            description="Jailbreak resistance must be validated before deployment",
            category="security",
            mandatory=True,
            owner="Security Team",
        ),
        PolicyItem(
            id="pol-3",
            title="PII Redaction",
            description="All outputs must be scanned for PII and redacted if found",
            category="privacy",
            mandatory=True,
            owner="Privacy Team",
        ),
        PolicyItem(
            id="pol-4",
            title="Content Moderation",
            description="All outputs must pass content moderation before delivery",
            category="safety",
            mandatory=True,
            owner="Safety Team",
        ),
        PolicyItem(
            id="pol-5",
            title="Human Review for High-Risk Outputs",
            description="Outputs flagged as high-risk require human review",
            category="safety",
            mandatory=True,
            owner="Safety Team",
        ),
        PolicyItem(
            id="pol-6",
            title="Incident Response Plan",
            description="An incident response plan must be maintained and tested quarterly",
            category="governance",
            mandatory=True,
            owner="Governance Team",
        ),
        PolicyItem(
            id="pol-7",
            title="Red Team Exercises",
            description="Red team exercises must be conducted monthly",
            category="security",
            mandatory=True,
            owner="Red Team",
        ),
        PolicyItem(
            id="pol-8",
            title="Bias and Fairness Audit",
            description="Models must pass bias and fairness audits",
            category="fairness",
            mandatory=True,
            owner="AI Ethics Team",
        ),
    ]

    def __init__(self):
        self._policies: dict[str, PolicyItem] = {}
        self._checklists: dict[str, ReviewChecklist] = {}
        self._load_defaults()

    def _load_defaults(self):
        for policy in self.DEFAULT_POLICIES:
            self._policies[policy.id] = policy

    def add_policy(self, policy: PolicyItem) -> PolicyItem:
        policy.id = policy.id or f"pol-{uuid.uuid4().hex[:8]}"
        policy.last_reviewed = time.time()
        self._policies[policy.id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Optional[PolicyItem]:
        return self._policies.get(policy_id)

    def get_policies(self, category: Optional[str] = None) -> list[PolicyItem]:
        policies = list(self._policies.values())
        if category:
            policies = [p for p in policies if p.category == category]
        return policies

    def create_checklist(self, name: str, items: list[dict]) -> ReviewChecklist:
        checklist_items = [
            ChecklistItem(
                id=item.get("id", f"cl-{uuid.uuid4().hex[:8]}"),
                description=item["description"],
                category=item.get("category", "general"),
                required=item.get("required", True),
            )
            for item in items
        ]
        checklist = ReviewChecklist(
            id=f"cl-{uuid.uuid4().hex[:8]}",
            name=name,
            items=checklist_items,
        )
        self._checklists[checklist.id] = checklist
        return checklist

    def get_checklist(self, checklist_id: str) -> Optional[ReviewChecklist]:
        return self._checklists.get(checklist_id)

    def update_checklist_item(self, checklist_id: str, item_id: str, passed: bool, reviewer: str, evidence: str = ""):
        checklist = self._checklists.get(checklist_id)
        if not checklist:
            return False
        for item in checklist.items:
            if item.id == item_id:
                item.passed = passed
                item.reviewer = reviewer
                item.evidence = evidence
                item.reviewed_at = time.time()
                checklist.status = "completed" if all(i.passed or not i.required for i in checklist.items) else "in_progress"
                return True
        return False

    def get_release_checklist(self) -> ReviewChecklist:
        items = [
            {"id": "rl-1", "description": "Prompt injection tests passed", "category": "security", "required": True},
            {"id": "rl-2", "description": "Jailbreak tests passed", "category": "security", "required": True},
            {"id": "rl-3", "description": "PII redaction verified", "category": "privacy", "required": True},
            {"id": "rl-4", "description": "Content moderation pipeline active", "category": "safety", "required": True},
            {"id": "rl-5", "description": "Safety scoring meets thresholds", "category": "safety", "required": True},
            {"id": "rl-6", "description": "Red team exercises completed", "category": "security", "required": True},
            {"id": "rl-7", "description": "Human feedback collected and reviewed", "category": "safety", "required": True},
            {"id": "rl-8", "description": "Incident response plan tested", "category": "governance", "required": True},
            {"id": "rl-9", "description": "Bias and fairness audit passed", "category": "fairness", "required": False},
            {"id": "rl-10", "description": "Documentation updated", "category": "governance", "required": False},
        ]
        return self.create_checklist("release_review", items)


governance_policy = GovernancePolicy()
