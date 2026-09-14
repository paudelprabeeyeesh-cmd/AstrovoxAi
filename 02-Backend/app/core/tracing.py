import contextlib
import logging
import uuid

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
        OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace.set_tracer_provider(
        TracerProvider(resource=Resource.create({"service.name": "astrovoxai"}))
    )
    tracer = trace.get_tracer(__name__)
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    tracer = None
    OPENTELEMETRY_AVAILABLE = False


@contextlib.contextmanager
def _noop_span():
    yield None


def start_trace(name: str, user_id: str, attributes: dict = None):
    if not OPENTELEMETRY_AVAILABLE or tracer is None:
        return _noop_span()
    span = tracer.start_as_current_span(name)
    span.set_attribute("user_id", user_id)
    span.set_attribute("request_id", str(uuid.uuid4()))
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return span


def log_llm_call(
    prompt_hash: str,
    model: str,
    tokens: int,
    cost: float,
    latency_ms: float,
    cached: bool = False,
):
    logger.info(
        f"LLM_CALL: prompt_hash={prompt_hash}, model={model}, tokens={tokens}, "
        f"cost={cost}, latency_ms={latency_ms}, cached={cached}"
    )


def get_prompt_hash(prompt: str) -> str:
    import hashlib

    return hashlib.sha256(prompt.encode()).hexdigest()[:16]
