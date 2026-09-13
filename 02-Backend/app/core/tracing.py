import logging
import time
import uuid
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "astrovoxai"})
    )
)
tracer = trace.get_tracer(__name__)


def start_trace(name: str, user_id: str, attributes: dict = None) -> trace.Span:
    span = tracer.start_as_current_editor(name)
    span.set_attribute("user_id", user_id)
    span.set_attribute("request_id", str(uuid.uuid4()))
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return span


def log_llm_call(prompt_hash: str, model: str, tokens: int, cost: float, latency_ms: float, cached: bool = False):
    logger.info(
        f"LLM_CALL: prompt_hash={prompt_hash}, model={model}, tokens={tokens}, "
        f"cost={cost}, latency_ms={latency_ms}, cached={cached}"
    )


def get_prompt_hash(prompt: str) -> str:
    import hashlib
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]
