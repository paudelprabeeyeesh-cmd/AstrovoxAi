from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReasoningStep:
    premise: str
    inference_type: str
    conclusion: str
    confidence: float


class AbstractReasoningEngine:
    def __init__(self):
        self.reasoning_chain: list[ReasoningStep] = []
        self.knowledge_graph: dict[str, list[str]] = {}

    def add_knowledge(self, concept: str, relations: list[str]):
        self.knowledge_graph[concept] = relations

    def reason(self, premise: str, target: str) -> ReasoningStep | None:
        if premise not in self.knowledge_graph:
            return None
        relations = self.knowledge_graph[premise]
        if target in relations:
            step = ReasoningStep(
                premise=premise,
                inference_type="deduction",
                conclusion=target,
                confidence=0.9,
            )
            self.reasoning_chain.append(step)
            return step
        for related in relations:
            if related in self.knowledge_graph and target in self.knowledge_graph[related]:
                step = ReasoningStep(
                    premise=premise,
                    inference_type="abduction",
                    conclusion=target,
                    confidence=0.7,
                )
                self.reasoning_chain.append(step)
                return step
        return None
