"""
Compliance reports for AstrovoxAI.
Generates reports for SOC 2, GDPR, HIPAA, and other compliance frameworks.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"


class ControlStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ControlResult:
    control_id: str
    name: str
    status: ControlStatus
    evidence: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "control_id": self.control_id,
            "name": self.name,
            "status": self.status.value,
            "evidence": self.evidence,
            "notes": self.notes,
        }


@dataclass
class ComplianceReport:
    report_id: str
    framework: ComplianceFramework
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    controls: List[ControlResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    pdf_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "framework": self.framework.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "controls": [c.to_dict() for c in self.controls],
            "summary": self.summary,
            "pdf_url": self.pdf_url,
        }


class ComplianceReportGenerator:
    """Generates compliance reports for various frameworks."""

    def __init__(self, audit_logger: Optional[Any] = None):
        self._audit_logger = audit_logger
        self._frameworks = self._initialize_frameworks()

    def _initialize_frameworks(self) -> Dict[ComplianceFramework, List[ControlResult]]:
        return {
            ComplianceFramework.SOC2: [
                ControlResult(control_id="CC6.1", name="Logical and Physical Access Controls", status=ControlStatus.COMPLIANT),
                ControlResult(control_id="CC6.6", name="System Boundaries Protection", status=ControlStatus.COMPLIANT),
                ControlResult(control_id="CC7.1", name="Detection of Changes", status=ControlStatus.COMPLIANT),
            ],
            ComplianceFramework.GDPR: [
                ControlResult(control_id="Art.5", name="Principles Relating to Processing", status=ControlStatus.COMPLIANT),
                ControlResult(control_id="Art.32", name="Security of Processing", status=ControlStatus.COMPLIANT),
            ],
            ComplianceFramework.HIPAA: [
                ControlResult(control_id="164.312", name="Technical Safeguards", status=ControlStatus.COMPLIANT),
                ControlResult(control_id="164.316", name="Policies and Procedures", status=ControlStatus.COMPLIANT),
            ],
        }

    def generate_report(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime,
    ) -> ComplianceReport:
        controls = self._frameworks.get(framework, [])
        compliant = sum(1 for c in controls if c.status == ControlStatus.COMPLIANT)
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            generated_at=datetime.utcnow(),
            controls=controls,
            summary={
                "total_controls": len(controls),
                "compliant": compliant,
                "compliance_rate": compliant / len(controls) if controls else 0.0,
            },
        )
        logger.info("Generated %s compliance report %s", framework.value, report.report_id)
        return report

    def list_frameworks(self) -> List[str]:
        return [f.value for f in ComplianceFramework]
