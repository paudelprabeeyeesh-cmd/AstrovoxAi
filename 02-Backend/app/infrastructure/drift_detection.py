"""Infrastructure drift detection for Terraform and Kubernetes."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DriftCategory(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    TAGGING = "tagging"
    SECURITY = "security"
    ENCRYPTION = "encryption"


@dataclass
class ResourceState:
    resource_id: str
    resource_type: str
    provider: str
    region: str
    attributes: Dict[str, Any]
    tags: Dict[str, str]
    last_known_hash: str = ""
    detected_at: float = field(default_factory=time.time)


@dataclass
class DriftDetection:
    detection_id: str
    resource_id: str
    category: DriftCategory
    severity: DriftSeverity
    expected_value: Any
    actual_value: Any
    description: str = ""
    detected_at: float = field(default_factory=time.time)
    remediation: Optional[str] = None


@dataclass
class DriftReport:
    report_id: str
    scan_id: str
    resource_states: List[ResourceState]
    detections: List[DriftDetection]
    scanned_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0

    @property
    def has_critical_drifts(self) -> bool:
        return any(d.severity == DriftSeverity.CRITICAL for d in self._detections)

    @property
    def critical_count(self) -> int:
        return sum(1 for d in self._detections if d.severity == DriftSeverity.CRITICAL)

    @property
    def total_drifts(self) -> int:
        return len(self._detections)


class TerraformDriftDetector:
    """Detect infrastructure drift using Terraform plan/apply outputs."""

    def __init__(self, terraform_path: str = "./infrastructure/terraform") -> None:
        self._terraform_path = terraform_path
        self._known_states: Dict[str, ResourceState] = {}
        self._drift_history: List[DriftReport] = []

    def record_known_state(self, state: ResourceState) -> None:
        self._known_states[state.resource_id] = state

    def get_known_state(self, resource_id: str) -> Optional[ResourceState]:
        return self._known_states.get(resource_id)

    def detect_drift(self, reported_states: List[ResourceState]) -> DriftReport:
        scan_id = f"scan_{int(time.time())}"
        detections: List[DriftDetection] = []
        for reported in reported_states:
            known = self._known_states.get(reported.resource_id)
            if not known:
                detections.append(self._create_detection(
                    resource_id=reported.resource_id,
                    category=DriftCategory.ADDED,
                    severity=DriftSeverity.INFO,
                    expected_value="not_present",
                    actual_value=reported.attributes,
                    description="Resource exists but not in known state",
                ))
                continue
            if known.tags != reported.tags:
                detections.append(self._create_detection(
                    resource_id=reported.resource_id,
                    category=DriftCategory.TAGGING,
                    severity=DriftSeverity.LOW,
                    expected_value=known.tags,
                    actual_value=reported.tags,
                    description="Resource tags have drifted",
                ))
            known_hash = self._compute_hash(known.attributes)
            reported_hash = self._compute_hash(reported.attributes)
            if known_hash != reported_hash:
                detections.append(self._create_detection(
                    resource_id=reported.resource_id,
                    category=DriftCategory.MODIFIED,
                    severity=DriftSeverity.MEDIUM,
                    expected_value=known.attributes,
                    actual_value=reported.attributes,
                    description="Resource attributes have drifted",
                    remediation="Run `terraform apply` to reconcile or update known state if intentional",
                ))
        report = DriftReport(
            report_id=f"report_{int(time.time())}",
            scan_id=scan_id,
            resource_states=reported_states,
            detections=detections,
        )
        self._drift_history.append(report)
        return report

    def _compute_hash(self, obj: Any) -> str:
        return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

    def _create_detection(
        self,
        resource_id: str,
        category: DriftCategory,
        severity: DriftSeverity,
        expected_value: Any,
        actual_value: Any,
        description: str,
        remediation: Optional[str] = None,
    ) -> DriftDetection:
        return DriftDetection(
            detection_id=f"drift_{int(time.time())}_{hashlib.md5(resource_id.encode()).hexdigest()[:8]}",
            resource_id=resource_id,
            category=category,
            severity=severity,
            expected_value=expected_value,
            actual_value=actual_value,
            description=description,
            remediation=remediation,
        )

    def get_recent_reports(self, limit: int = 10) -> List[DriftReport]:
        return self._drift_history[-limit:]


class KubernetesDriftDetector:
    """Detect Kubernetes resource drift from GitOps manifests."""

    def __init__(self) -> None:
        self._known_states: Dict[str, ResourceState] = {}
        self._drift_history: List[DriftReport] = []

    def record_known_state(self, state: ResourceState) -> None:
        self._known_states[state.resource_id] = state

    def get_known_state(self, resource_id: str) -> Optional[ResourceState]:
        return self._known_states.get(resource_id)

    def detect_drift(self, cluster_resources: List[ResourceState]) -> DriftReport:
        scan_id = f"k8s_scan_{int(time.time())}"
        detections: List[DriftDetection] = []
        for reported in cluster_resources:
            known = self._known_states.get(reported.resource_id)
            if not known:
                detections.append(self._create_detection(
                    resource_id=reported.resource_id,
                    category=DriftCategory.ADDED,
                    severity=DriftSeverity.INFO,
                    expected_value="not_present",
                    actual_value=reported.attributes,
                    description="Cluster resource not found in GitOps manifests",
                ))
                continue
            known_hash = hashlib.sha256(json.dumps(known.attributes, sort_keys=True, default=str).encode()).hexdigest()
            reported_hash = hashlib.sha256(json.dumps(reported.attributes, sort_keys=True, default=str).encode()).hexdigest()
            if known_hash != reported_hash:
                detections.append(self._create_detection(
                    resource_id=reported.resource_id,
                    category=DriftCategory.MODIFIED,
                    severity=DriftSeverity.HIGH,
                    expected_value=known.attributes,
                    actual_value=reported.attributes,
                    description="Cluster resource differs from GitOps manifests",
                    remediation="Apply GitOps manifests with `kubectl apply` or ArgoCD sync",
                ))
        report = DriftReport(
            report_id=f"k8s_report_{int(time.time())}",
            scan_id=scan_id,
            resource_states=cluster_resources,
            detections=detections,
        )
        self._drift_history.append(report)
        return report

    def _create_detection(
        self,
        resource_id: str,
        category: DriftCategory,
        severity: DriftSeverity,
        expected_value: Any,
        actual_value: Any,
        description: str,
        remediation: Optional[str] = None,
    ) -> DriftDetection:
        return DriftDetection(
            detection_id=f"k8s_drift_{int(time.time())}_{hashlib.md5(resource_id.encode()).hexdigest()[:8]}",
            resource_id=resource_id,
            category=category,
            severity=severity,
            expected_value=expected_value,
            actual_value=actual_value,
            description=description,
            remediation=remediation,
        )

    def get_recent_reports(self, limit: int = 10) -> List[DriftReport]:
        return self._drift_history[-limit:]


_terraform_detector: Optional[TerraformDriftDetector] = None
_k8s_detector: Optional[KubernetesDriftDetector] = None


def get_terraform_drift_detector() -> TerraformDriftDetector:
    global _terraform_detector
    if _terraform_detector is None:
        _terraform_detector = TerraformDriftDetector()
    return _terraform_detector


def get_k8s_drift_detector() -> KubernetesDriftDetector:
    global _k8s_detector
    if _k8s_detector is None:
        _k8s_detector = KubernetesDriftDetector()
    return _k8s_detector
