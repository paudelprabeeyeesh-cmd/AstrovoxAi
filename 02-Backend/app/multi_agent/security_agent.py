"""Security agent — vulnerability scanning and threat modeling."""

import logging
import re

from app.multi_agent import Agent, AgentConfig, AgentRole
from app.safety.injection_defense import InputSanitizer, PatternDetector

logger = logging.getLogger(__name__)


class SecurityAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.SECURITY, config)
        self.input_sanitizer = InputSanitizer()
        self.pattern_detector = PatternDetector()

    def execute(self, artifact: str, artifact_type: str = "code") -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "artifact_type": artifact_type}]
        findings = self._scan(artifact, artifact_type)
        steps.append({"step": "scanned", "findings": findings})
        self.transition_to(self.state.COMPLETED)
        return {"output": findings, "steps": steps}

    def _scan(self, artifact: str, artifact_type: str) -> list[dict]:
        findings = []
        sanitized = self.input_sanitizer.sanitize(artifact)
        if sanitized != artifact:
            findings.append({"severity": "high", "type": "injection", "detail": "Input sanitization triggered"})
        patterns = self.pattern_detector.scan(artifact)
        for p in patterns:
            findings.append({"severity": p.threat_level, "type": "pattern", "detail": p.reason})
        if artifact_type == "code" and re.search(r"eval\\(|exec\\(", artifact):
            findings.append({"severity": "critical", "type": "unsafe_code", "detail": "Use of eval/exec detected"})
        return findings


def create_security_agent(name: str = "security-agent") -> SecurityAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.SECURITY.value,
        system_prompt="You are a security agent. Scan for vulnerabilities and enforce safe coding practices.",
        model="gpt-4",
        temperature=0.0,
        max_tokens=2000,
        tool_whitelist=["file_read"],
    )
    return SecurityAgent(config)
