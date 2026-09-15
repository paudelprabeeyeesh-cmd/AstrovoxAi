import contextlib
import functools
import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

OPENTELEMETRY_AVAILABLE = False
tracer = None


def _noop_span():
    @contextlib.contextmanager
    def _cm():
        yield None
    return _cm()


class _TraceLLMCallContext:
    def __init__(self, *, operation, model, provider):
        self.operation = operation
        self.model = model
        self.provider = provider
        self.span = None
        self._cm = None

    def __enter__(self):
        if not OPENTELEMETRY_AVAILABLE or tracer is None:
            self.span = None
            return self.span
        self._cm = tracer.start_as_current_span(self.operation)
        self.span = self._cm.__enter__()
        if self.model:
            self.span.set_attribute("llm.model", self.model)
        if self.provider:
            self.span.set_attribute("llm.provider", self.provider)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cm is not None:
            return self._cm.__exit__(exc_type, exc_val, exc_tb)
        return False

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                if self.span is not None:
                    self.span.set_attribute("llm.function", func.__name__)
                return func(*args, **kwargs)
        return wrapper


def trace_llm_call(func=None, *, operation="llm.generate", model=None, provider=None):
    """Trace LLM calls. Can be used as a decorator or context manager.

    As context manager:
        with trace_llm_call(model="gpt-4", provider="openai") as span:
            # call llm
            if span:
                span.set_attribute("llm.tokens", 100)

    As decorator:
        @trace_llm_call
        def call_llm(...): ...

        @trace_llm_call(operation="custom.llm", model="gpt-4")
        def call_llm(...): ...
    """
    if func is not None and callable(func):
        ctx = _TraceLLMCallContext(operation=operation, model=model, provider=provider)
        return ctx(func)
    return _TraceLLMCallContext(operation=operation, model=model, provider=provider)


def init_tracing(service_name: str = "astrovoxai", app=None):
    """Initialize OpenTelemetry distributed tracing.

    Sets up a TracerProvider with ConsoleSpanExporter by default,
    or OTLPSpanExporter if OTEL_EXPORTER_OTLP_ENDPOINT is set.
    Instruments FastAPI, httpx, and psycopg2 if available.
    """
    global OPENTELEMETRY_AVAILABLE, tracer

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        logger.warning("OpenTelemetry packages not installed; tracing disabled")
        OPENTELEMETRY_AVAILABLE = False
        tracer = None
        return None

    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

        otlp_endpoint = (
            os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        )
        if otlp_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )

        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer(__name__)
        OPENTELEMETRY_AVAILABLE = True

        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor().instrument(app)
            except Exception as e:
                logger.warning(f"Failed to instrument FastAPI: {e}")

        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument httpx: {e}")

        try:
            from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
            Psycopg2Instrumentor().instrument()
        except Exception as e:
            logger.warning(f"Failed to instrument psycopg2: {e}")

        logger.info("OpenTelemetry tracing initialized")
        return tracer

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        OPENTELEMETRY_AVAILABLE = False
        tracer = None
        return None


def start_trace(name: str, user_id: str, attributes: dict = None):
    """Start a trace span. Returns a context manager."""
    if not OPENTELEMETRY_AVAILABLE or tracer is None:
        return _noop_span()

    @contextlib.contextmanager
    def _cm():
        with tracer.start_as_current_span(name) as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("request_id", str(uuid.uuid4()))
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    return _cm()


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
