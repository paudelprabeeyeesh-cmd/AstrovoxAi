import logging
from typing import Any

from .planner import PlannerAgent
from .coder import CoderAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from .reviewer import ReviewerAgent
from .debugger import DebuggerAgent
from .base import AgentResult, Plan, Review
from ..planning import PlanningEngine
from ..decomposition import TaskDecomposer, TaskNode
from ..debate import DebateEngine
from ..self_eval import SelfEvaluator, Evaluation
from ..memory_conflict import MemoryConflictDetector, Conflict

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client
        self.agents = {
            "planner": PlannerAgent(llm_client),
            "coder": CoderAgent(llm_client),
            "researcher": ResearcherAgent(llm_client),
            "writer": WriterAgent(llm_client),
            "reviewer": ReviewerAgent(llm_client),
            "debugger": DebuggerAgent(llm_client),
        }
        self.planning_engine = PlanningEngine(llm_client)
        self.decomposer = TaskDecomposer(llm_client)
        self.debate_engine = DebateEngine(llm_client)
        self.self_evaluator = SelfEvaluator(llm_client)
        self.conflict_detector = MemoryConflictDetector()

    def execute_workflow(self, workflow_name: str, task: str, context: dict[str, Any] | None = None, user_approval: bool = False) -> AgentResult:
        plan = self.planning_engine.create_plan(task, context)
        task_tree = self.decomposer.decompose(task, max_depth=3)

        if user_approval:
            logger.info(f"Plan for workflow '{workflow_name}': {[st.description for st in plan.subtasks]}")

        result = self.planning_engine.execute_plan(plan)
        output = "\n".join(r.get("output", "") for r in result.get("results", []))

        evaluation = self.self_evaluator.evaluate_response(task, output, context)
        self.self_evaluator.log_evaluation(task, output, evaluation)

        logger.info(f"Workflow '{workflow_name}' executed: success={result.get('success', False)}")
        return AgentResult(
            success=result.get("success", False),
            output=output,
            metadata={
                "plan": plan,
                "task_tree": task_tree,
                "evaluation": evaluation,
            },
        )

    def route_task(self, task: str) -> str:
        task_lower = task.lower()
        if any(kw in task_lower for kw in ["plan", "schedule", "roadmap"]):
            return "planner"
        if any(kw in task_lower for kw in ["code", "implement", "build"]):
            return "coder"
        if any(kw in task_lower for kw in ["debug", "fix", "error"]):
            return "debugger"
        if any(kw in task_lower for kw in ["research", "find", "search", "analyze"]):
            return "researcher"
        if any(kw in task_lower for kw in ["write", "draft", "compose"]):
            return "writer"
        if any(kw in task_lower for kw in ["review", "check", "evaluate"]):
            return "reviewer"
        return "planner"

    def run_debate(self, proposal: str, agents: list[str]) -> dict[str, Any]:
        return self.debate_engine.round(proposal, agents)

    def detect_memory_conflicts(self, memories: list[dict[str, Any]]) -> list[Conflict]:
        return self.conflict_detector.detect_conflicts(memories)

    def resolve_memory_conflict(self, conflict: Conflict, strategy: str = "newest") -> dict[str, Any]:
        return self.conflict_detector.resolve_conflict(conflict, strategy)
