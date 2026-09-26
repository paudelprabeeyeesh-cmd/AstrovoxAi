from typing import List, Callable, Any
from dataclasses import dataclass, field


@dataclass
class PipelineStep:
    name: str
    fn: Callable[[Any], Any]
    params: dict = field(default_factory=dict)


class MLPipeline:
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    def run(self, context: Any) -> Any:
        for step in self.steps:
            context = step.fn(context)
        return context
