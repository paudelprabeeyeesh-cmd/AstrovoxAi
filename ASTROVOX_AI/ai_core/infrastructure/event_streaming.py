from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from collections import defaultdict
import threading
from ASTROVOX_AI.ai_core.infrastructure.message_queue import MessageQueue


class EventStreaming:
    def __init__(self, message_queue: Optional[MessageQueue] = None):
        self.message_queue = message_queue or MessageQueue()
        self.topics: Dict[str, List[Callable]] = defaultdict(list)
        self.event_log: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.consumer_threads: List[threading.Thread] = []
        self.running = False

    def subscribe(self, topic: str, handler: Callable) -> None:
        self.topics[topic].append(handler)

    def publish(self, topic: str, event: Dict[str, Any]) -> None:
        event['topic'] = topic
        event['timestamp'] = datetime.now().isoformat()
        event['event_id'] = f"{topic}:{len(self.event_log)}"
        with self.lock:
            self.event_log.append(event)
        self.message_queue.publish(topic, event)

    def start_consumers(self, num_consumers: int = 2) -> None:
        self.running = True
        for _ in range(num_consumers):
            t = threading.Thread(target=self._consume_loop, daemon=True)
            t.start()
            self.consumer_threads.append(t)

    def _consume_loop(self) -> None:
        while self.running:
            msg = self.message_queue.consume(self.event_log[-1].get('topic', '') if self.event_log else '', timeout=1.0)
            if msg:
                topic = msg.get('topic', '')
                for handler in self.topics.get(topic, []):
                    try:
                        handler(msg.get('payload', {}))
                    except Exception:
                        logger.warning("event handler failed", exc_info=True)

    def stop(self) -> None:
        self.running = False
        for t in self.consumer_threads:
            t.join()
