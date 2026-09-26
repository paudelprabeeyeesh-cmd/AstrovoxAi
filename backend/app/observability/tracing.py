from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def setup_tracing(service_name: str, endpoint: str) -> None:
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
