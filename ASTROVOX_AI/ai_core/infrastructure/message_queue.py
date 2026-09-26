from typing import Optional, Dict, Any, List
from datetime import datetime
from ASTROVOX_AI.ai_core.distributed.distributed_task_queue import DistributedTaskQueue


class MessageQueue:
    def __init__(self, backend: str = 'memory', broker_url: Optional[str] = None, max_queue_size: int = 10000):
        self.backend = backend
        self.broker_url = broker_url
        self.max_queue_size = max_queue_size
        self.task_queue = DistributedTaskQueue(max_size=max_queue_size)
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self.processed_count = 0
        self.failed_count = 0

    def publish(self, topic: str, message: Dict[str, Any], priority: int = 0) -> None:
        envelope = {'topic': topic, 'payload': message, 'timestamp': datetime.now().isoformat(), 'priority': priority}
        self.task_queue.put(envelope, priority=priority)

    def consume(self, topic: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        while True:
            msg = self.task_queue.get(block=True, timeout=timeout)
            if msg is None:
                return None
            if msg.get('topic') == topic:
                self.processed_count += 1
                return msg
            self.task_queue.put(msg, priority=msg.get('priority', 0))

    def retry(self, message: Dict[str, Any], max_retries: int = 3) -> bool:
        retries = message.get('retries', 0)
        if retries < max_retries:
            message['retries'] = retries + 1
            self.task_queue.put(message, priority=message.get('priority', 0))
            return True
        self.dead_letter_queue.append(message)
        self.failed_count += 1
        return False

    def get_stats(self) -> Dict[str, int]:
        return {'processed': self.processed_count, 'failed': self.failed_count, 'dead_letter': len(self.dead_letter_queue), 'queue_size': self.task_queue.size()}
