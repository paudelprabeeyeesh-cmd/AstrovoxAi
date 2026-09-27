"""Terraform module definitions."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TerraformModule:
    module_id: str
    name: str
    source: str
    variables: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)


@dataclass
class TerraformPlan:
    plan_id: str
    modules: List[TerraformModule]
    status: str = "planned"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TerraformManager:
    def __init__(self) -> None:
        self._modules: Dict[str, TerraformModule] = {}
        self._plans: Dict[str, TerraformPlan] = {}

    def register_module(self, module: TerraformModule) -> None:
        self._modules[module.module_id] = module

    def create_plan(self, plan: TerraformPlan) -> TerraformPlan:
        self._plans[plan.plan_id] = plan
        return plan


terraform_manager = TerraformManager()
