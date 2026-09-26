from typing import Optional, Dict, Any
from ASTROVOX_AI.ai_core.distributed.distributed_tracing import DistributedTracer


class ServiceMesh:
    def __init__(self, service_name: str, collector_url: Optional[str] = None, retry_attempts: int = 3, timeout: float = 5.0):
        self.service_name = service_name
        self.tracer = DistributedTracer(service_name, collector_url)
        self.retry_attempts = retry_attempts
        self.timeout = timeout
        self.services: Dict[str, Dict[str, Any]] = {}

    def register_service(self, name: str, endpoint: str, version: str = 'v1', metadata: Optional[Dict[str, Any]] = None) -> None:
        self.services[name] = {'endpoint': endpoint, 'version': version, 'metadata': metadata or {}, 'status': 'healthy'}

    def call_service(self, service_name: str, method: str, path: str, **kwargs) -> Dict[str, Any]:
        span = self.tracer.start_span(trace_id=kwargs.get('trace_id', 'unknown'), span_id=kwargs.get('span_id', 'unknown'), operation=f'{service_name}.{method}.{path}')
        try:
            service = self.services.get(service_name)
            if not service:
                span.set_tag('error', 'Service not found')
                span.finish()
                return {'error': 'Service not found'}
            url = f"{service['endpoint']}{path}"
            import requests
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            span.set_tag('http.status_code', response.status_code)
            span.finish()
            return response.json() if response.headers.get('content-type', '').startswith('application/json') else {'body': response.text}
        except Exception as e:
            span.set_tag('error', str(e))
            span.finish()
            return {'error': str(e)}

    def health_check(self, service_name: str) -> Dict[str, Any]:
        try:
            result = self.call_service(service_name, 'GET', '/health')
            self.services[service_name]['status'] = 'healthy' if 'error' not in result else 'unhealthy'
            return result
        except Exception:
            self.services[service_name]['status'] = 'unhealthy'
            return {'status': 'unhealthy'}
