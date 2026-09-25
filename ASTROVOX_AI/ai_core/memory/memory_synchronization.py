from typing import Optional, Dict, Any, List
import threading
import time
from datetime import datetime
from ASTROVOX_AI.ai_core.memory.memory_decay import MemoryDecay


class MemorySynchronization:
    def __init__(self, source_node: str, target_nodes: List[str], sync_interval: float = 60.0):
        self.source_node = source_node
        self.target_nodes = target_nodes
        self.sync_interval = sync_interval
        self.decay = MemoryDecay()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_sync: Optional[datetime] = None

    def start(self, get_memories: callable, send_to_node: callable) -> None:
        self.running = True
        self.get_memories = get_memories
        self.send_to_node = send_to_node
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()

    def _sync_loop(self) -> None:
        while self.running:
            memories = self.get_memories()
            decayed = self.decay.batch_decay(memories)
            for node in self.target_nodes:
                self.send_to_node(node, decayed)
            self.last_sync = datetime.now()
            time.sleep(self.sync_interval)

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join()

    def sync_now(self) -> None:
        memories = self.get_memories()
        decayed = self.decay.batch_decay(memories)
        for node in self.target_nodes:
            self.send_to_node(node, decayed)
        self.last_sync = datetime.now()
