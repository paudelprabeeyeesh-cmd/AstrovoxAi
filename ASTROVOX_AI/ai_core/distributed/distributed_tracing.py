from typing import Dict, Any, Optional, List
from datetime import datetime


class Span:
    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None, operation: str = ''):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.operation = operation
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.tags: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []
        self.status = 'ok'

    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value

    def log(self, message: str, **kwargs) -> None:
        self.logs.append({'timestamp': datetime.now().isoformat(), 'message': message, **kwargs})

    def finish(self) -> None:
        self.end_time = datetime.now()
        self.status = 'ok' if self.status == 'ok' else 'error'

    def to_dict(self) -> Dict[str, Any]:
        return {'trace_id': self.trace_id, 'span_id': self.span_id, 'parent_span_id': self.parent_span_id, 'operation': self.operation, 'start_time': self.start_time.isoformat(), 'end_time': self.end_time.isoformat() if self.end_time else None, 'duration_ms': (self.end_time - self.start_time).total_seconds() * 1000 if self.end_time else None, 'tags': self.tags, 'status': self.status}


class DistributedTracer:
    def __init__(self, service_name: str, collector_url: Optional[str] = None):
        self.service_name = service_name
        self.collector_url = collector_url
        self.spans: Dict[str, Span] = {}
        self.active_spans: Dict[str, Span] = {}

    def start_span(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None, operation: str = '') -> Span:
        span = Span(trace_id, span_id, parent_span_id, operation)
        span.set_tag('service', self.service_name)
        self.spans[span_id] = span
        self.active_spans[span_id] = span
        return span

    def finish_span(self, span_id: str) -> None:
        if span_id in self.active_spans:
            span = self.active_spans.pop(span_id)
            span.finish()

    def inject(self, headers: Dict[str, str], span: Span) -> None:
        headers['X-Trace-ID'] = span.trace_id
        headers['X-Span-ID'] = span.span_id

    def extract(self, headers: Dict[str, str]) -> Optional[Span]:
        trace_id = headers.get('X-Trace-ID')
        span_id = headers.get('X-Span-ID')
        if trace_id and span_id:
            return self.spans.get(span_id)
        return None

    def export(self) -> List[Dict[str, Any]]:
        return [span.to_dict() for span in self.spans.values() if span.end_time is not None]
