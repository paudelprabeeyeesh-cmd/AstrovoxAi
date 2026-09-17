import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ThreatCategory(Enum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threat:
    id: str
    name: str
    category: ThreatCategory
    description: str
    subsystem: str
    severity: Severity = Severity.MEDIUM
    affected_assets: list[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    threat: Threat
    likelihood: str
    impact: str
    risk_score: int
    residual_risk: str


@dataclass
class Mitigation:
    id: str
    threat_id: str
    description: str
    priority: str
    implementation_notes: str = ""


class ThreatModel:
    def identify_threats(self, subsystem: str) -> list[Threat]:
        threats: list[Threat] = []
        base_id = f"{subsystem}_"

        threat_definitions = [
            ("auth_brute_force", "Authentication Brute Force", ThreatCategory.DENIAL_OF_SERVICE, "Credential stuffing and brute force attacks against login endpoints"),
            ("auth_token_forgery", "Token Forgery", ThreatCategory.SPOOFING, "Attackers forge or guess JWT tokens to impersonate users"),
            ("auth_privilege_escalation", "Privilege Escalation", ThreatCategory.ELEVATION_OF_PRIVILEGE, "Horizontal or vertical privilege escalation via parameter tampering"),
            ("data_exfiltration", "Data Exfiltration", ThreatCategory.INFORMATION_DISCLOSURE, "Unauthorized access to sensitive user data or model outputs"),
            ("input_injection", "Input Injection", ThreatCategory.TAMPERING, "Prompt injection or malicious payload injection into model inputs"),
            ("supply_chain_compromise", "Supply Chain Compromise", ThreatCategory.TAMPERING, "Malicious dependencies or compromised model artifacts"),
            ("dos_overload", "Denial of Service Overload", ThreatCategory.DENIAL_OF_SERVICE, "Resource exhaustion via high-volume requests"),
            ("audit_log_tampering", "Audit Log Tampering", ThreatCategory.REPUDIATION, "Deletion or alteration of audit logs to hide malicious activity"),
        ]

        for idx, (name_key, title, category, desc) in enumerate(threat_definitions, start=1):
            threats.append(
                Threat(
                    id=f"{base_id}{idx:03d}",
                    name=title,
                    category=category,
                    description=desc,
                    subsystem=subsystem,
                    severity=Severity.HIGH if category in {ThreatCategory.ELEVATION_OF_PRIVILEGE, ThreatCategory.INFORMATION_DISCLOSURE} else Severity.MEDIUM,
                    affected_assets=[subsystem],
                )
            )

        logger.info(f"Identified {len(threats)} threats for subsystem '{subsystem}'")
        return threats

    def assess_risk(self, threat: Threat) -> RiskAssessment:
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
        elif risk_score >= 25:
            residual_risk = "medium"
        else:
            residual_risk = "high"

        return RiskAssessment(
            threat=threat,
            likelihood=str(likelihood),
            impact=str(impact),
            risk_score=risk_score,
            residual_risk=residual_risk,
        )

    def generate_mitigations(self, threat: Threat) -> list[Mitigation]:
        mitigations: list[Mitigation] = []
        base_id = f"mit_{threat.id}"

        mitigation_templates = {
            ThreatCategory.SPOOFING: [
                ("enforce_mtls", "Enforce mutual TLS and strong token validation", "high"),
                ("rotate_credentials", "Implement short-lived tokens with automatic rotation", "high"),
            ],
            ThreatCategory.TAMPERING: [
                ("integrity_checks", "Enable cryptographic integrity checks on all inputs", "high"),
                ("sandbox_execution", "Run untrusted code in isolated sandboxed environments", "medium"),
            ],
            ThreatCategory.REPUDIATION: [
                ("immutable_audit_logs", "Write audit logs to immutable storage with write-once semantics", "high"),
                ("centralized_logging", "Ship logs to tamper-evident centralized logging", "medium"),
            ],
            ThreatCategory.INFORMATION_DISCLOSURE: [
                ("encrypt_data_rest", "Encrypt all sensitive data at rest and in transit", "high"),
                ("least_privilege_access", "Apply least privilege access controls and row-level security", "high"),
                ("data_masking", "Mask sensitive fields in logs and non-production environments", "medium"),
            ],
            ThreatCategory.DENIAL_OF_SERVICE: [
                ("rate_limiting", "Implement adaptive rate limiting per user and endpoint", "high"),
                ("auto_scaling", "Deploy auto-scaling groups with burst capacity", "medium"),
                ("ddos_protection", "Enable DDoS protection at the edge (WAF/CDN)", "high"),
            ],
            ThreatCategory.ELEVATION_OF_PRIVILEGE: [
                ("rbac_enforcement", "Enforce role-based access control on every request", "high"),
                ("input_validation", "Validate and sanitize all privilege-related input parameters", "high"),
            ],
        }

        templates = mitigation_templates.get(threat.category, [("review_architecture", "Review architecture for additional attack surfaces", "medium")])

        for idx, (name, description, priority) in enumerate(templates, start=1):
            mitigations.append(
                Mitigation(
                    id=f"{base_id}_{idx}",
                    threat_id=threat.id,
                    description=description,
                    priority=priority,
                )
            )

        return mitigations
