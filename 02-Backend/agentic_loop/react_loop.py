import time
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime


@dataclass
class ReActStep:
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReActResult:
    steps: List[ReActStep]
    final_answer: Optional[str]
    success: bool
    total_time: float
    iterations: int


class ExponentialBackoff:
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, multiplier: float = 2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.attempt = 0

    def get_delay(self) -> float:
        delay = self.base_delay * (self.multiplier ** self.attempt)
        delay = min(delay, self.max_delay)
        jitter = random.uniform(0, 0.1 * delay)
        self.attempt += 1
        return delay + jitter

    def reset(self) -> None:
        self.attempt = 0


class ReActLoop:
    def __init__(
        self,
        tools: Dict[str, Callable],
        max_iterations: int = 10,
        backoff: Optional[ExponentialBackoff] = None,
    ):
        self.tools = tools
        self.max_iterations = max_iterations
        self.backoff = backoff or ExponentialBackoff()

    def run(self, query: str, llm_callback: Callable[[str, List[ReActStep]], str]) -> ReActResult:
        steps: List[ReActStep] = []
        start_time = time.time()
        iteration = 0
        final_answer = None

        while iteration < self.max_iterations:
            try:
                react_output = llm_callback(query, steps)
                step = self._parse_react_output(react_output)
                steps.append(step)

                if step.action and step.action.lower() == "finish":
                    final_answer = step.action_input.get("answer", "") if step.action_input else ""
                    break

                if step.action and step.action in self.tools:
                    try:
                        result = self.tools[step.action](**(step.action_input or {}))
                        step.observation = str(result)
                    except Exception as e:
                        step.observation = f"Error: {str(e)}"
                        delay = self.backoff.get_delay()
                        time.sleep(delay)
                        step.error = str(e)
                elif step.action:
                    step.observation = f"Unknown tool: {step.action}"

            except Exception as e:
                step = ReActStep(thought=f"Error during iteration {iteration}", error=str(e))
                steps.append(step)
                delay = self.backoff.get_delay()
                time.sleep(delay)

            iteration += 1

        total_time = time.time() - start_time
        return ReActResult(
            steps=steps,
            final_answer=final_answer,
            success=final_answer is not None and len(final_answer) > 0,
            total_time=total_time,
            iterations=iteration,
        )

    def _parse_react_output(self, output: str) -> ReActStep:
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
                import json
                try:
                    action_input = json.loads(line[len("Action Input:"):].strip())
                except Exception:
                    action_input = {}

        return ReActStep(thought=thought or "No thought provided", action=action, action_input=action_input)
