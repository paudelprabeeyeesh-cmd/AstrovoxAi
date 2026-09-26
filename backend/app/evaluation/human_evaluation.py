from dataclasses import dataclass
from typing import List, Dict, Any
import uuid


@dataclass
class HumanEvaluationTask:
    task_id: str
    input: str
    output_a: str
    output_b: str
    criteria: List[str]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.task_id is None:
            self.task_id = str(uuid.uuid4())


class HumanEvaluationManager:
    def __init__(self):
        self.tasks: List[HumanEvaluationTask] = []

    def create_task(self, input_text: str, output_a: str, output_b: str, criteria: List[str]) -> HumanEvaluationTask:
        task = HumanEvaluationTask(
            task_id=None,
            input=input_text,
            output_a=output_a,
            output_b=output_b,
            criteria=criteria,
        )
        self.tasks.append(task)
        return task
