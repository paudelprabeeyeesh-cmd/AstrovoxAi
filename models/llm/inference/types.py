import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class InferenceError(Exception):
    pass


class InvalidRequestError(InferenceError):
    pass


@dataclass
class SamplingParams:
    temperature: float = 1.0
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float = 1.0
    max_new_tokens: int = 100
    stop: list[str] | None = None
    priority: int = 0


@dataclass
class GenerationOutput:
    text: str
    token_ids: list[int]
    num_tokens: int
    finish_reason: str
    prompt_tokens: int
    latency_ms: float
