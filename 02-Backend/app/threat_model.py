"""Threat modeling templates and STRIDE/PASTA methodology support.

This module provides comprehensive threat modeling with:

1. STRIDE threat categorization (Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege)
2. PASTA threat modeling process support
3. Automated threat identification for subsystems
4. Risk assessment with likelihood/impact matrix
5. Mitigation strategy generation
6. Threat library with common patterns
7. Compliance mapping (SOC2, GDPR, PCI-DSS, HIPAA)
8. Attack tree generation
9. Data flow diagram (DFD) support

Threat model: OWASP Threat Modeling, Microsoft STRIDE, PASTA
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class STRIDECategory(str, Enum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class PASTAStep(str, Enum):
    OBJECTIVE = "objective"
    DEFINE = "define"
    EXPLORE = "explore"
    ATTACK = "attack"
    VULNERABILITIES = "vulnerabilities"
    ATTACK_TREE = "attack_tree"
    ANALYSIS = "analysis"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"
    NIST = "nist"
    ISO27001 = "iso27001"


@dataclass
class Threat:
    id: str
    name: str
    category: STRIDECategory
    description: str
    subsystem: str
    severity: Severity = Severity.MEDIUM
    affected_assets: List[str] = field(default_factory=list)
    mitigation_status: str = "identified"
    compliance_mappings: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    threat: Threat
    likelihood: str
    impact: str
    risk_score: int
    residual_risk: str
    mitigation_priority: str


@dataclass
class Mitigation:
    id: str
    threat_id: str
    description: str
    priority: str
    implementation_notes: str = ""
    compliance_mappings: List[str] = field(default_factory=list)
    status: str = "planned"


@dataclass
class AttackTreeNode:
    goal: str
    children: List["AttackTreeNode"] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    likelihood: str = "medium"


@dataclass
class DataFlow:
    source: str
    destination: str
    data_type: str
    protocol: str
    is_encrypted: bool = False
    trust_boundary: str = ""


class ThreatModel:
    """Comprehensive threat modeling with STRIDE/PASTA support."""

    def __init__(self):
        self._threats: List[Threat] = []
        self._mitigations: List[Mitigation] = []
        self._risk_assessments: List[RiskAssessment] = []
        self._data_flows: List[DataFlow] = []
        self._lock = __import__('threading').Lock()
        self._threat_library = self._build_threat_library()

    def _build_threat_library(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build comprehensive threat library."""
        return {
            "auth": [
                {
                    "name": "Credential Stuffing",
                    "category": STRIDECategory.SPOOFING,
                    "severity": Severity.HIGH,
                    "description": "Attackers use leaked credentials to gain unauthorized access",
                    "affected_assets": ["authentication", "user_accounts"],
                    "compliance_mappings": ["OWASP_A07", "PCI_Req_8", "SOC2_CC6"],
                },
                {
                    "name": "Session Hijacking",
                    "category": STRIDECategory.SPOOFING,
                    "severity": Severity.CRITICAL,
                    "description": "Attackers steal session tokens to impersonate legitimate users",
                    "affected_assets": ["sessions", "jwt_tokens"],
                    "compliance_mappings": ["OWASP_A02", "SOC2_CC6"],
                },
                {
                    "name": "JWT Token Forgery",
                    "category": STRIDECategory.SPOOFING,
                    "severity": Severity.CRITICAL,
                    "description": "Attackers forge JWT tokens with weak or no signature verification",
                    "affected_assets": ["jwt_tokens", "api_gateway"],
                    "compliance_mappings": ["OWASP_A02", "OWASP_A08"],
                },
            ],
            "api": [
                {
                    "name": "API Abuse / Scraping",
                    "category": STRIDECategory.DENIAL_OF_SERVICE,
                    "severity": Severity.MEDIUM,
                    "description": "Automated tools abuse API endpoints to extract data",
                    "affected_assets": ["api_endpoints", "rate_limits"],
                    "compliance_mappings": ["OWASP_A04", "SOC2_CC7"],
                },
                {
                    "name": "Parameter Tampering",
                    "category": STRIDECategory.TAMPERING,
                    "severity": Severity.HIGH,
                    "description": "Attackers modify request parameters to bypass authorization",
                    "affected_assets": ["api_inputs", "authorization"],
                    "compliance_mappings": ["OWASP_A01", "SOC2_CC6"],
                },
                {
                    "name": "Response Tampering",
                    "category": STRIDECategory.TAMPERING,
                    "severity": Severity.HIGH,
                    "description": "Man-in-the-middle attacks modify API responses",
                    "affected_assets": ["api_responses", "tls"],
                    "compliance_mappings": ["OWASP_A02", "PCI_Req_4"],
                },
            ],
            "data": [
                {
                    "name": "Data Exfiltration",
                    "category": STRIDECategory.INFORMATION_DISCLOSURE,
                    "severity": Severity.CRITICAL,
                    "description": "Unauthorized access and extraction of sensitive data",
                    "affected_assets": ["databases", "user_data"],
                    "compliance_mappings": ["GDPR_Art_5", "HIPAA_164", "PCI_Req_3"],
                },
                {
                    "name": "SQL Injection",
                    "category": STRIDECategory.TAMPERING,
                    "severity": Severity.CRITICAL,
                    "description": "SQL injection attacks modify or extract database data",
                    "affected_assets": ["databases", "orm_queries"],
                    "compliance_mappings": ["OWASP_A03", "PCI_Req_6"],
                },
                {
                    "name": "Insecure Direct Object Reference",
                    "category": STRIDECategory.ELEVATION_OF_PRIVILEGE,
                    "severity": Severity.HIGH,
                    "description": "Attackers access unauthorized resources via direct references",
                    "affected_assets": ["api_endpoints", "authorization"],
                    "compliance_mappings": ["OWASP_A01", "SOC2_CC6"],
                },
            ],
            "ai": [
                {
                    "name": "Prompt Injection",
                    "category": STRIDECategory.TAMPERING,
                    "severity": Severity.HIGH,
                    "description": "Malicious inputs manipulate AI model behavior",
                    "affected_assets": ["ai_models", "prompt_engine"],
                    "compliance_mappings": ["OWASP_LLM01", "MITRE_ATLAS"],
                },
                {
                    "name": "Data Poisoning",
                    "category": STRIDECategory.TAMPERING,
                    "severity": Severity.CRITICAL,
                    "description": "Malicious training data corrupts model behavior",
                    "affected_assets": ["training_data", "model_weights"],
                    "compliance_mappings": ["OWASP_LLM04", "NIST_AI_RMF"],
                },
                {
                    "name": "Model Inversion",
                    "category": STRIDECategory.INFORMATION_DISCLOSURE,
                    "severity": Severity.HIGH,
                    "description": "Attackers reconstruct training data from model outputs",
                    "affected_assets": ["ai_models", "training_data"],
                    "compliance_mappings": ["GDPR_Art_5", "HIPAA_164"],
                },
            ],
        }

    def identify_threats(self, subsystem: str, include_library: bool = True) -> List[Threat]:
        """Identify threats for a subsystem using library and generic patterns."""
        threats: List[Threat] = []
        base_id = f"{subsystem}_"

        if include_library and subsystem in self._threat_library:
            for idx, threat_data in enumerate(self._threat_library[subsystem], start=1):
                threats.append(Threat(
                    id=f"{base_id}{idx:03d}",
                    name=threat_data["name"],
                    category=threat_data["category"],
                    description=threat_data["description"],
                    subsystem=subsystem,
                    severity=threat_data.get("severity", Severity.MEDIUM),
                    affected_assets=threat_data.get("affected_assets", [subsystem]),
                    compliance_mappings=threat_data.get("compliance_mappings", []),
                ))

        # Add generic threats
        generic_threats = [
            ("denial_of_service", "Denial of Service Overload", STRIDECategory.DENIAL_OF_SERVICE,
             "Resource exhaustion via high-volume requests", Severity.MEDIUM),
            ("audit_log_tampering", "Audit Log Tampering", STRIDECategory.REPUDIATION,
             "Deletion or alteration of audit logs to hide malicious activity", Severity.HIGH),
            ("supply_chain", "Supply Chain Compromise", STRIDECategory.TAMPERING,
             "Malicious dependencies or compromised model artifacts", Severity.HIGH),
            ("config_exposure", "Configuration Exposure", STRIDECategory.INFORMATION_DISCLOSURE,
             "Sensitive configuration data exposed via errors or debugging", Severity.MEDIUM),
        ]

        start_idx = len(threats) + 1
        for idx, (name_key, title, category, desc, severity) in enumerate(generic_threats, start=start_idx):
            threats.append(Threat(
                id=f"{base_id}{idx:03d}",
                name=title,
                category=category,
                description=desc,
                subsystem=subsystem,
                severity=severity,
                affected_assets=[subsystem],
            ))

        with self._lock:
            self._threats.extend(threats)

        logger.info("Identified %d threats for subsystem '%s'", len(threats), subsystem)
        return threats

    def assess_risk(self, threat: Threat) -> RiskAssessment:
        """Assess risk for a threat using likelihood/impact matrix."""
        severity_map = {
            Severity.LOW: (2, 1),
            Severity.MEDIUM: (5, 3),
            Severity.HIGH: (8, 6),
            Severity.CRITICAL: (10, 8),
        }
        likelihood, impact = severity_map.get(threat.severity, (5, 3))
        risk_score = likelihood * impact

        if risk_score >= 60:
            residual_risk = "low"
            mitigation_priority = "high"
        elif risk_score >= 25:
            residual_risk = "medium"
            mitigation_priority = "medium"
        else:
            residual_risk = "high"
            mitigation_priority = "low"

        assessment = RiskAssessment(
            threat=threat,
            likelihood=str(likelihood),
            impact=str(impact),
            risk_score=risk_score,
            residual_risk=residual_risk,
        )
        with self._lock:
            self._risk_assessments.append(assessment)

        return assessment

    def generate_mitigations(self, threat: Threat, framework: Optional[ComplianceFramework] = None) -> List[Mitigation]:
        """Generate mitigation strategies for a threat."""
        mitigations: List[Mitigation] = []
        base_id = f"mit_{threat.id}"

        stride_mitigations = {
            STRIDECategory.SPOOFING: [
                ("enforce_mtls", "Enforce mutual TLS and strong token validation with restricted algorithms", "high", ["SOC2_CC6", "PCI_Req_4"]),
                ("rotate_credentials", "Implement short-lived tokens with automatic rotation and replay detection", "high", ["SOC2_CC6", "OWASP_A02"]),
                ("mfa_enforcement", "Require multi-factor authentication for all sensitive operations", "high", ["PCI_Req_8", "SOC2_CC6"]),
            ],
            STRIDECategory.TAMPERING: [
                ("integrity_checks", "Enable cryptographic integrity checks on all inputs and outputs", "high", ["OWASP_A08", "SOC2_CC7"]),
                ("sandbox_execution", "Run untrusted code in isolated sandboxed environments", "medium", ["SOC2_CC7"]),
                ("input_validation", "Validate and sanitize all inputs using schema validation", "high", ["OWASP_A03", "PCI_Req_6"]),
                ("immutable_storage", "Store critical data in append-only immutable storage", "high", ["SOC2_CC7", "GDPR_Art_5"]),
            ],
            STRIDECategory.REPUDIATION: [
                ("immutable_audit_logs", "Write audit logs to immutable storage with write-once semantics", "high", ["SOC2_CC7", "HIPAA_164"]),
                ("centralized_logging", "Ship logs to tamper-evident centralized logging", "medium", ["SOC2_CC7"]),
                ("digital_signatures", "Sign critical actions with user digital signatures", "high", ["SOC2_CC6"]),
            ],
            STRIDECategory.INFORMATION_DISCLOSURE: [
                ("encrypt_data_rest", "Encrypt all sensitive data at rest and in transit", "high", ["GDPR_Art_32", "PCI_Req_3", "HIPAA_164"]),
                ("least_privilege_access", "Apply least privilege access controls and row-level security", "high", ["SOC2_CC6", "GDPR_Art_5"]),
                ("data_masking", "Mask sensitive fields in logs and non-production environments", "medium", ["PCI_Req_3", "GDPR_Art_5"]),
                ("pii_detection", "Implement PII detection and automatic redaction", "high", ["GDPR_Art_5", "CCPA"]),
            ],
            STRIDECategory.DENIAL_OF_SERVICE: [
                ("rate_limiting", "Implement adaptive rate limiting per user and endpoint", "high", ["SOC2_CC7", "OWASP_A04"]),
                ("auto_scaling", "Deploy auto-scaling groups with burst capacity", "medium", ["SOC2_A1"]),
                ("ddos_protection", "Enable DDoS protection at the edge (WAF/CDN)", "high", ["SOC2_CC7"]),
                ("circuit_breakers", "Implement circuit breakers for downstream dependencies", "medium", ["SOC2_A1"]),
            ],
            STRIDECategory.ELEVATION_OF_PRIVILEGE: [
                ("rbac_enforcement", "Enforce role-based access control on every request", "high", ["SOC2_CC6", "OWASP_A01"]),
                ("input_validation", "Validate and sanitize all privilege-related input parameters", "high", ["OWASP_A03", "PCI_Req_6"]),
                ("segregation_of_duties", "Implement segregation of duties for sensitive operations", "high", ["SOC2_CC2", "SOX"]),
            ],
        }

        templates = stride_mitigations.get(threat.category, [
            ("review_architecture", "Review architecture for additional attack surfaces", "medium", []),
        ])

        for idx, (name, description, priority, mappings) in enumerate(templates, start=1):
            mitigations.append(Mitigation(
                id=f"{base_id}_{idx}",
                threat_id=threat.id,
                description=description,
                priority=priority,
                implementation_notes=f"Implemented as part of {threat.subsystem} security hardening",
                compliance_mappings=mappings,
                status="planned",
            ))

        with self._lock:
            self._mitigations.extend(mitigations)

        return mitigations

    def build_attack_tree(self, root_goal: str, threats: List[Threat]) -> AttackTreeNode:
        """Build an attack tree for a specific goal."""
        root = AttackTreeNode(goal=root_goal)

        # Group threats by STRIDE category
        by_category: Dict[STRIDECategory, List[Threat]] = {}
        for threat in threats:
            by_category.setdefault(threat.category, []).append(threat)

        for category, category_threats in by_category.items():
            category_node = AttackTreeNode(
                goal=f"{category.value} attacks",
                children=[],
                likelihood="medium",
            )
            for threat in category_threats:
                threat_node = AttackTreeNode(
                    goal=threat.name,
                    children=[],
                    likelihood=threat.severity.value,
                    mitigations=[m.id for m in self._mitigations if m.threat_id == threat.id],
                )
                category_node.children.append(threat_node)
            root.children.append(category_node)

        return root

    def add_data_flow(self, source: str, destination: str, data_type: str,
                      protocol: str, is_encrypted: bool = False, trust_boundary: str = "") -> DataFlow:
        """Add a data flow to the threat model."""
        flow = DataFlow(
            source=source,
            destination=destination,
            data_type=data_type,
            protocol=protocol,
            is_encrypted=is_encrypted,
            trust_boundary=trust_boundary,
        )
        with self._lock:
            self._data_flows.append(flow)
        return flow

    def analyze_data_flows(self) -> List[Dict[str, Any]]:
        """Analyze data flows for security issues."""
        findings = []
        with self._lock:
            for flow in self._data_flows:
                if not flow.is_encrypted and flow.protocol not in ("localhost", "unix"):
                    findings.append({
                        "data_flow": flow.__dict__,
                        "issue": "unencrypted_data_transfer",
                        "severity": "high",
                        "recommendation": f"Enable TLS for {flow.protocol} communication",
                    })
                if not flow.trust_boundary:
                    findings.append({
                        "data_flow": flow.__dict__,
                        "issue": "missing_trust_boundary",
                        "severity": "medium",
                        "recommendation": "Define trust boundary for this data flow",
                    })
        return findings

    def generate_compliance_report(self, framework: ComplianceFramework) -> Dict[str, Any]:
        """Generate compliance-specific threat report."""
        with self._lock:
            mapped_threats = []
            for threat in self._threats:
                mappings = [m for m in threat.compliance_mappings if framework.value.upper() in m.upper()]
                if mappings:
                    mapped_threats.append({
                        "threat_id": threat.id,
                        "threat_name": threat.name,
                        "severity": threat.severity.value,
                        "compliance_mappings": mappings,
                        "mitigations": [
                            m.description for m in self._mitigations
                            if m.threat_id == threat.id and framework.value.upper() in str(m.compliance_mappings).upper()
                        ],
                    })

            return {
                "framework": framework.value,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_threats": len(mapped_threats),
                "mapped_threats": mapped_threats,
                "coverage": len(mapped_threats) / max(1, len(self._threats)),
            }

    def get_full_model(self) -> Dict[str, Any]:
        """Get complete threat model."""
        with self._lock:
            return {
                "threats": [t.__dict__ for t in self._threats],
                "risk_assessments": [r.__dict__ for r in self._risk_assessments],
                "mitigations": [m.__dict__ for m in self._mitigations],
                "data_flows": [d.__dict__ for d in self._data_flows],
                "stats": {
                    "total_threats": len(self._threats),
                    "critical_threats": sum(1 for t in self._threats if t.severity == Severity.CRITICAL),
                    "high_threats": sum(1 for t in self._threats if t.severity == Severity.HIGH),
                    "mitigations_planned": sum(1 for m in self._mitigations if m.status == "planned"),
                    "mitigations_implemented": sum(1 for m in self._mitigations if m.status == "implemented"),
                },
            }

    def export_model(self, format: str = "json") -> str:
        """Export the threat model in various formats."""
        model = self.get_full_model()
        if format == "json":
            return json.dumps(model, default=str, indent=2)
        elif format == "markdown":
            lines = ["# Threat Model Report", ""]
            for threat in model["threats"]:
                lines.append(f"## {threat['id']}: {threat['name']}")
                lines.append(f"- **Category:** {threat['category']}")
                lines.append(f"- **Severity:** {threat['severity']}")
                lines.append(f"- **Subsystem:** {threat['subsystem']}")
                lines.append("")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


threat_model = ThreatModel()


def identify_subsystem_threats(subsystem: str) -> List[Threat]:
    """Convenience function to identify threats for a subsystem."""
    return threat_model.identify_threats(subsystem)


def assess_threat_risk(threat: Threat) -> RiskAssessment:
    """Convenience function to assess threat risk."""
    return threat_model.assess_risk(threat)


def generate_threat_mitigations(threat: Threat) -> List[Mitigation]:
    """Convenience function to generate mitigations."""
    return threat_model.generate_mitigations(threat)
