"""Constitutional AI for AI safety."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ViolationSeverity(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Principle:
    name: str
    description: str
    keywords: List[str]
    severity: ViolationSeverity
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Principle) and self.name == other.name


@dataclass
class Constitution:
    name: str
    description: str
    principles: List[Principle]
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_principle(self, name: str) -> Optional[Principle]:
        for p in self.principles:
            if p.name == name:
                return p
        return None

    def add_principle(self, principle: Principle):
        existing = self.get_principle(principle.name)
        if existing is None:
            self.principles.append(principle)
        else:
            existing.keywords = list(set(existing.keywords + principle.keywords))
            existing.severity = principle.severity


@dataclass
class Violation:
    principle: Principle
    confidence: float
    evidence: str
    severity: ViolationSeverity
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    compliant: bool
    violations: List[Violation] = field(default_factory=list)
    overall_score: float = 1.0
    flagged_principles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


DEFAULT_CONSTITUTION = Constitution(
    name="AstrovoxAI Constitution",
    description="Core principles for safe and beneficial AI.",
    principles=[
        Principle(
            name="No Harm",
            description="Output must not cause physical, emotional, or psychological harm.",
            keywords=["harm", "hurt", "injure", "damage", "kill", "attack", "assault", "abuse"],
            severity=ViolationSeverity.CRITICAL,
        ),
        Principle(
            name="No Hate",
            description="Output must not promote hatred, discrimination, or hostility toward individuals or groups.",
            keywords=["hate", "racist", "bigot", "supremacist", "slur", "discriminate", "hostile"],
            severity=ViolationSeverity.CRITICAL,
        ),
        Principle(
            name="No Deception",
            description="Output must not intentionally mislead, lie, or deceive.",
            keywords=["lie", "deceive", "mislead", "fraud", "scam", "pretend", "fake", "hoax"],
            severity=ViolationSeverity.HIGH,
        ),
        Principle(
            name="Privacy",
            description="Output must protect personal data and respect confidentiality.",
            keywords=["password", "secret", "private", "personal", "confidential", "ssn", "credit card", "address"],
            severity=ViolationSeverity.HIGH,
        ),
        Principle(
            name="Accuracy",
            description="Output must be truthful, evidence-based, and not fabricate information.",
            keywords=["lie", "fake", "fabricate", "invent", "hallucinate", "make up", "false"],
            severity=ViolationSeverity.MEDIUM,
        ),
        Principle(
            name="Autonomy",
            description="Output must respect human autonomy and must not manipulate or coerce.",
            keywords=["manipulate", "coerce", "force", "compel", "dominate", "control"],
            severity=ViolationSeverity.HIGH,
        ),
        Principle(
            name="Fairness",
            description="Output must not discriminate on the basis of protected characteristics.",
            keywords=["discriminate", "bias", "unfair", "prejudiced", "stereotype", "racist", "sexist"],
            severity=ViolationSeverity.HIGH,
        ),
    ],
)


class ConstitutionalAI:
    def __init__(self, constitution: Optional[Constitution] = None):
        self.constitution = constitution or DEFAULT_CONSTITUTION

    def check(self, text: str) -> ComplianceReport:
        violations: List[Violation] = []
        lowered = text.lower()

        for principle in self.constitution.principles:
            evidence = self._find_evidence(lowered, principle.keywords)
            if evidence:
                confidence = min(len(evidence) / max(len(principle.keywords), 1), 1.0)
                violations.append(Violation(
                    principle=principle,
                    confidence=confidence,
                    evidence="; ".join(evidence[:5]),
                    severity=principle.severity,
                ))

        overall_score = self._compute_score(violations)
        flagged = list({v.principle.name for v in violations})
        compliant = len(violations) == 0 or overall_score >= 0.7

        return ComplianceReport(
            compliant=compliant,
            violations=violations,
            overall_score=overall_score,
            flagged_principles=flagged,
        )

    def _find_evidence(self, text: str, keywords: List[str]) -> List[str]:
        found = []
        for kw in keywords:
            if kw in text:
                found.append(kw)
        return found

    def _compute_score(self, violations: List[Violation]) -> float:
        if not violations:
            return 1.0
        penalty = 0.0
        for v in violations:
            sev_map = {
                ViolationSeverity.LOW: 0.05,
                ViolationSeverity.MEDIUM: 0.15,
                ViolationSeverity.HIGH: 0.30,
                ViolationSeverity.CRITICAL: 0.50,
            }
            penalty += sev_map.get(v.severity, 0.1) * v.confidence
        return max(0.0, 1.0 - min(penalty, 1.0))

    def add_principle(self, principle: Principle):
        self.constitution.add_principle(principle)

    def get_constitution(self) -> Constitution:
        return self.constitution

    def check_batch(self, texts: List[str]) -> List[ComplianceReport]:
        return [self.check(text) for text in texts]

    def summarize(self, report: ComplianceReport) -> str:
        if report.compliant:
            return f"Compliant (score={report.overall_score:.2f})"
        violations_str = "; ".join(
            f"{v.principle.name}({v.severity.value}, {v.confidence:.2f})"
            for v in report.violations
        )
        return f"Violations: {violations_str} (score={report.overall_score:.2f})"


constitutional_ai = ConstitutionalAI()
