from typing import Optional, Dict, Any, List, Tuple
from ASTROVOX_AI.ai_core.distributed.distributed_tracing import DistributedTracer


class AgentCommunicationProtocol:
    def __init__(self, agent_id: str, tracer: Optional[DistributedTracer] = None):
        self.agent_id = agent_id
        self.tracer = tracer
        self.message_handlers: Dict[str, callable] = {}
        self.inbox: List[Dict[str, Any]] = []
        self.outbox: List[Dict[str, Any]] = []

    def register_handler(self, message_type: str, handler: callable) -> None:
        self.message_handlers[message_type] = handler

    def send(self, recipient_id: str, message_type: str, payload: Dict[str, Any], priority: int = 0) -> str:
        message = {'from': self.agent_id, 'to': recipient_id, 'type': message_type, 'payload': payload, 'priority': priority, 'timestamp': datetime.now().isoformat()}
        self.outbox.append(message)
        return message.get('message_id', str(hash(str(message))))

    def receive(self, message: Dict[str, Any]) -> Optional[Any]:
        self.inbox.append(message)
        message_type = message.get('type', '')
        handler = self.message_handlers.get(message_type)
        if handler:
            if self.tracer:
                span = self.tracer.start_span(message.get('trace_id', 'unknown'), message.get('message_id', 'unknown'), operation=f'agent.{message_type}')
                result = handler(message.get('payload', {}))
                span.finish()
                return result
            return handler(message.get('payload', {}))
        return None

    def broadcast(self, message_type: str, payload: Dict[str, Any], recipients: List[str]) -> List[str]:
        return [self.send(recipient, message_type, payload) for recipient in recipients]
