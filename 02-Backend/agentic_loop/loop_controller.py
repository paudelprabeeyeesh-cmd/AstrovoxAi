import json
from typing import Any, Callable, Dict, List

from agentic_loop.action_executor import ActionExecutor, ActionResult
from agentic_loop.feedback_integrator import Feedback, FeedbackIntegrator
from agentic_loop.state_tracker import LoopStep, StateTracker


class LoopController:
    def __init__(
        self,
        max_iterations: int = 10,
        action_timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.max_iterations = max_iterations
        self.state_tracker = StateTracker()
        self.action_executor = ActionExecutor(timeout=action_timeout)
        self.feedback_integrator = FeedbackIntegrator(max_retries=max_retries)

    def run(self, query: str, tools: Dict[str, Callable], llm_callback: Callable[[str, List[LoopStep]], str]) -> Dict[str, Any]:
        self.state_tracker.initialize(query)
        iteration = 0
        final_answer = None

        while iteration < self.max_iterations:
            history = self.state_tracker.get_history()
            react_output = llm_callback(query, history)
            step = self._parse_output(react_output)
            self.state_tracker.add_step(step)

            if step.action and step.action.lower() == "finish":
                final_answer = step.action_input.get("answer", "") if step.action_input else ""
                self.state_tracker.update_status("completed")
                break

            if step.action and step.action in tools:
                result = self.action_executor.execute(step.action, step.action_input or {}, tools)
                step.observation = str(result.result) if result.result is not None else None
                step.error = result.error
                feedback = Feedback(
                    observation=step.observation,
                    error=step.error,
                    step_index=iteration,
                )
                self.feedback_integrator.integrate(self.state_tracker.state, feedback)
            elif step.action:
                step.observation = f"Unknown tool: {step.action}"
                step.error = f"Unknown tool: {step.action}"
            else:
                step.observation = "No action provided"
                step.error = "No action provided"

            iteration += 1
        else:
            self.state_tracker.update_status("max_iterations_reached")

        return {
            "steps": self.state_tracker.get_history(),
            "final_answer": final_answer,
            "success": final_answer is not None and len(final_answer) > 0,
            "iterations": iteration,
            "status": self.state_tracker.state.status,
        }

    def _parse_output(self, output: str) -> LoopStep:
        lines = output.strip().split("\n")
        thought = ""
        action = None
        action_input = None

        for line in lines:
            if line.startswith("Thought:"):
                thought = line[len("Thought:"):].strip()
            elif line.startswith("Action:"):
                action = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                try:
                    action_input = json.loads(line[len("Action Input:"):].strip())
                except Exception:  # noqa: BLE001
                    action_input = {}

        return LoopStep(thought=thought or "No thought provided", action=action, action_input=action_input)
