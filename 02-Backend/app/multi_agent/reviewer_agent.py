"""Reviewer agent — code review and quality assessment."""

import logging

from app.multi_agent import Agent, AgentConfig, AgentRole

logger = logging.getLogger(__name__)


class ReviewerAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole.REVIEWER, config)

    def execute(self, artifact: str, artifact_type: str = "code") -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "artifact_type": artifact_type}]
        review = self._review(artifact, artifact_type)
        steps.append({"step": "reviewed", "issues": review["issues"], "score": review["score"]})
        self.transition_to(self.state.COMPLETED)
        return {"output": review, "steps": steps}

    def _review(self, artifact: str, artifact_type: str) -> dict:
        issues = []
        if artifact_type == "code" and "import" not in artifact:
            issues.append("Missing imports")
        if len(artifact) < 10:
            issues.append("Artifact is too short")
        score = max(0.0, 1.0 - (len(issues) * 0.2))
        return {"score": round(score, 2), "issues": issues, "summary": "Review completed."}


def create_reviewer_agent(name: str = "reviewer-agent") -> ReviewerAgent:
    config = AgentConfig(
        name=name,
        role=AgentRole.REVIEWER.value,
        system_prompt="You are a reviewer agent. Assess quality, correctness, and style.",
        model="gpt-4",
        temperature=0.0,
        max_tokens=2000,
        tool_whitelist=["file_read"],
    )
    return ReviewerAgent(config)
