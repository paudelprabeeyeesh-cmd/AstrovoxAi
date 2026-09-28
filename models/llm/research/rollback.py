from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ChangeRecord:
    change_id: str
    author: str
    description: str
    timestamp: str
    diff_hash: str
    files_modified: List[str]
    impact_level: str


@dataclass
class ImpactAnalysis:
    component: str
    impact_level: str
    risk_score: float
    affected_tests: List[str]
    affected_components: List[str]
    rollback_difficulty: str


@dataclass
class RollbackProcedure:
    procedure_id: str
    name: str
    steps: List[str]
    estimated_time_minutes: int
    prerequisites: List[str]
    success_criteria: List[str]


@dataclass
class RollbackPlan:
    plan_id: str
    experiment_id: str
    baseline_commit: str
    changes: List[ChangeRecord]
    impact_analyses: List[ImpactAnalysis]
    procedures: List[RollbackProcedure]
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ChangeTracker:
    def __init__(self):
        self.changes: List[ChangeRecord] = []

    def record(self, change: ChangeRecord) -> ChangeRecord:
        self.changes.append(change)
        logger.info("Recorded change %s from %s", change.change_id, change.author)
        return change

    def history(self) -> List[Dict]:
        return [
            {
                "change_id": c.change_id,
                "author": c.author,
                "description": c.description,
                "timestamp": c.timestamp,
                "impact_level": c.impact_level,
                "files_modified": c.files_modified,
            }
            for c in self.changes
        ]


class RollbackPlanManager:
    def __init__(self, plan_id: str, experiment_id: str, baseline_commit: str):
        self.plan = RollbackPlan(plan_id=plan_id, experiment_id=experiment_id, baseline_commit=baseline_commit, changes=[], impact_analyses=[], procedures=[])
        self.change_tracker = ChangeTracker()

    def add_change(self, change: ChangeRecord) -> RollbackPlanManager:
        self.plan.changes.append(change)
        self.change_tracker.record(change)
        self.plan.updated_at = datetime.utcnow().isoformat() + "Z"
        return self

    def add_impact_analysis(self, analysis: ImpactAnalysis) -> RollbackPlanManager:
        self.plan.impact_analyses.append(analysis)
        return self

    def add_procedure(self, procedure: RollbackProcedure) -> RollbackPlanManager:
        self.plan.procedures.append(procedure)
        return self

    def activate(self) -> RollbackPlan:
        self.plan.status = "active"
        logger.info("Rollback plan %s activated", self.plan.plan_id)
        return self.plan

    def execute(self, procedure_id: str) -> Dict:
        for proc in self.plan.procedures:
            if proc.procedure_id == procedure_id:
                logger.info("Executing rollback procedure %s", proc.name)
                return {"status": "success", "procedure": proc.name, "steps_executed": proc.steps}
        return {"status": "not_found", "procedure_id": procedure_id}

    def cancel(self) -> RollbackPlan:
        self.plan.status = "cancelled"
        self.plan.updated_at = datetime.utcnow().isoformat() + "Z"
        logger.info("Rollback plan %s cancelled", self.plan.plan_id)
        return self.plan

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan.plan_id,
            "experiment_id": self.plan.experiment_id,
            "baseline_commit": self.plan.baseline_commit,
            "status": self.plan.status,
            "changes": self.change_tracker.history(),
            "impact_count": len(self.plan.impact_analyses),
            "procedure_count": len(self.plan.procedures),
            "created_at": self.plan.created_at,
            "updated_at": self.plan.updated_at,
        }
