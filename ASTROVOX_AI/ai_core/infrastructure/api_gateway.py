from typing import Optional, Dict, Any, List
from ASTROVOX_AI.ai_core.security.api_abuse_detection import APIAbuseDetector
from ASTROVOX_AI.ai_core.security.prompt_injection_defense import PromptInjectionDefense
from ASTROVOX_AI.ai_core.distributed.distributed_tracing import DistributedTracer


class APIGateway:
    def __init__(self, service_name: str, rate_limit: int = 100, block_threshold: int = 5, collector_url: Optional[str] = None):
        self.service_name = service_name
        self.abuse_detector = APIAbuseDetector(rate_limit=rate_limit, block_threshold=block_threshold)
        self.injection_defense = PromptInjectionDefense()
        self.tracer = DistributedTracer(service_name, collector_url)
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.middleware: List[callable] = []

    def add_route(self, path: str, method: str, handler: callable, auth_required: bool = False, rate_limit: Optional[int] = None) -> None:
        self.routes[f'{method}:{path}'] = {'path': path, 'method': method, 'handler': handler, 'auth_required': auth_required, 'rate_limit': rate_limit}

    def add_middleware(self, middleware: callable) -> None:
        self.middleware.append(middleware)

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        span = self.tracer.start_span(trace_id=request.get('trace_id', 'unknown'), span_id=request.get('span_id', 'unknown'), operation=f"api.{request.get('method', 'GET')}.{request.get('path', '/')}")
        ip = request.get('ip', 'unknown')
        allowed, reason = self.abuse_detector.record_request(ip, request.get('path', '/'), len(str(request.get('body', ''))))
        if not allowed:
            span.set_tag('error', reason)
            span.finish()
            return {'status': 429, 'body': {'error': reason}}
        if 'body' in request and isinstance(request['body'], str):
            is_injected, pattern = self.injection_defense.detect_injection(request['body'])
            if is_injected:
                span.set_tag('error', f'Injection detected: {pattern}')
                span.finish()
                return {'status': 400, 'body': {'error': 'Invalid request content'}}
        route_key = f"{request.get('method', 'GET')}:{request.get('path', '/')}"
        if route_key not in self.routes:
            span.set_tag('http.status_code', 404)
            span.finish()
            return {'status': 404, 'body': {'error': 'Not found'}}
        route = self.routes[route_key]
        for mw in self.middleware:
            result = mw(request)
            if result:
                return result
        span.set_tag('http.status_code', 200)
        span.finish()
        return {'status': 200, 'body': route['handler'](request)}
