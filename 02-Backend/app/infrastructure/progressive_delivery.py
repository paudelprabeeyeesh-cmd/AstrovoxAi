"""Progressive delivery configuration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeliveryStrategy(str, Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    A_B_TESTING = "a_b_testing"


@dataclass
class CanaryConfig:
    steps: List[Dict[str, Any]] = field(default_factory=list)
    analysis_template_name: str = "success-rate"
    success_condition: str = "result[0] >= 0.95"


@dataclass
class BlueGreenConfig:
    active_service: str = "astrovox"
    preview_service: str = "astrovox-preview"
    auto_promotion_enabled: bool = True
    auto_promotion_max_unavailable: int = 1
    scale_down_delay_seconds: int = 30


@dataclass
class ProgressiveDeliveryConfig:
    strategy: DeliveryStrategy = DeliveryStrategy.CANARY
    canary: CanaryConfig = field(default_factory=CanaryConfig)
    blue_green: BlueGreenConfig = field(default_factory=BlueGreenConfig)
    analysis_enabled: bool = True
    rollback_on_failure: bool = True


class ProgressiveDeliveryManager:
    """Manage progressive delivery configurations."""

    def __init__(self, config: ProgressiveDeliveryConfig) -> None:
        self._config = config

    def get_canary_rollout(self) -> Dict[str, Any]:
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Rollout",
            "metadata": {"name": "astrovox", "namespace": "astrovox"},
            "spec": {
                "replicas": 3,
                "strategy": {
                    "canary": {
                        "steps": self._config.canary.steps,
                        "analysis": {
                            "templates": [
                                {
                                    "name": self._config.canary.analysis_template_name,
                                    "spec": {
                                        "successCondition": self._config.canary.success_condition,
                                    },
                                }
                            ]
                        },
                    }
                },
                "selector": {"matchLabels": {"app": "astrovox"}},
                "template": {
                    "metadata": {"labels": {"app": "astrovox"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "astrovox",
                                "image": "astrovox:latest",
                                "ports": [{"containerPort": 8000}],
                            }
                        ]
                    },
                },
            },
        }

    def get_blue_green_rollout(self) -> Dict[str, Any]:
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Rollout",
            "metadata": {"name": "astrovox", "namespace": "astrovox"},
            "spec": {
                "replicas": 3,
                "strategy": {
                    "blueGreen": {
                        "activeService": self._config.blue_green.active_service,
                        "previewService": self._config.blue_green.preview_service,
                        "autoPromotionEnabled": self._config.blue_green.auto_promotion_enabled,
                        "autoPromotionMaxUnavailable": self._config.blue_green.auto_promotion_max_unavailable,
                        "scaleDownDelaySeconds": self._config.blue_green.scale_down_delay_seconds,
                    }
                },
                "selector": {"matchLabels": {"app": "astrovox"}},
                "template": {
                    "metadata": {"labels": {"app": "astrovox", "version": "stable"}},
                    "spec": {
                        "containers": [
                            {
                                "name": "astrovox",
                                "image": "astrovox:latest",
                                "ports": [{"containerPort": 8000}],
                            }
                        ]
                    },
                },
            },
        }


_delivery_manager: Optional[ProgressiveDeliveryManager] = None


def get_progressive_delivery_manager() -> ProgressiveDeliveryManager:
    global _delivery_manager
    if _delivery_manager is None:
        _delivery_manager = ProgressiveDeliveryManager(
            config=ProgressiveDeliveryConfig()
        )
    return _delivery_manager
