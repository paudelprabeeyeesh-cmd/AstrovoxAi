"""Testing agent — test generation and coverage analysis."""

import logging
import re

from app.multi_agent import Agent, AgentConfig, AgentRole

logger = logging.getLogger(__name__)


class TestingAgent(Agent):
    def __init__(self, config: AgentConfig):
        super().__init__(AgentRole(AgentRole.TESTING.value if hasattr(AgentRole, "TESTING") else "planner"), config)

    def execute(self, artifact: str, artifact_type: str = "code") -> dict:
        self.transition_to(self.state.RUNNING)
        steps = [{"step": "received", "artifact_type": artifact_type}]
        tests = self._generate_tests(artifact, artifact_type)
        coverage = self._estimate_coverage(artifact, tests)
        steps.append({"step": "generated", "test_count": len(tests), "coverage": coverage})
        self.transition_to(self.state.COMPLETED)
        return {"output": tests, "steps": steps}

    def _generate_tests(self, artifact: str, artifact_type: str) -> list[str]:
        tests = []
        if artifact_type == "code":
            functions = re.findall(r"def\\s+(\\w+)\\(\\s*([^)]*)\\)", artifact)
            for func_name, params in functions:
                tests.append(f"def test_{func_name}():\\n    assert {func_name}() is not None")
        return tests

    def _estimate_coverage(self, artifact: str, tests: list[str]) -> float:
        if not tests or not artifact:
            return 0.0
        lines = len([l for l in artifact.splitlines() if l.strip()])
        return min(len(tests) * 10 / max(lines, 1), 1.0)


def create_testing_agent(name: str = "testing-agent") -> TestingAgent:
    config = AgentConfig(
        name=name,
        role="testing",
        system_prompt="You are a testing agent. Generate unit tests and estimate coverage.",
        model="gpt-4",
        temperature=0.0,
        max_tokens=2000,
        tool_whitelist=["file_read", "file_write"],
    )
    return TestingAgent(config)
