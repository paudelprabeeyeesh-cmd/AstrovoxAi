"""
Multi-agent orchestrator with message passing and deadlock prevention.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))


@dataclass
class Agent:
    agent_id: str
    role: str
    capabilities: List[str]
    handler: Callable
    max_concurrent: int = 1
    timeout_seconds: float = 30.0


class MessageQueue:
    """Thread-safe message queue for agent communication."""

    def __init__(self):
        self.queue: deque = deque()
        self.lock = threading.Lock()
        self.delivered: Set[str] = set()

    def send(self, message: AgentMessage):
        with self.lock:
            self.queue.append(message)

    def receive(self, receiver_id: str) -> Optional[AgentMessage]:
        with self.lock:
            for i, msg in enumerate(self.queue):
                if msg.receiver == receiver_id and msg.message_id not in self.delivered:
                    self.delivered.add(msg.message_id)
                    return self.queue[i]
        return None

    def has_pending(self, receiver_id: str) -> bool:
        with self.lock:
            return any(m.receiver == receiver_id and m.message_id not in self.delivered for m in self.queue)


class MultiAgentOrchestrator:
    """Orchestrates multiple agents with message passing and deadlock prevention."""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_queue = MessageQueue()
        self.agent_states: Dict[str, str] = {}
        self.wait_for_graph: Dict[str, Set[str]] = defaultdict(set)
        self.results: Dict[str, Any] = {}
        self.lock = threading.Lock()

    def register_agent(self, agent: Agent):
        self.agents[agent.agent_id] = agent
        self.agent_states[agent.agent_id] = "idle"
        logger.info("Registered agent: %s (role: %s)", agent.agent_id, agent.role)

    def send_message(self, sender: str, receiver: str, content: Any) -> str:
        message = AgentMessage(sender=sender, receiver=receiver, content=content)
        self.message_queue.send(message)
        with self.lock:
            self.wait_for_graph[sender].add(receiver)
        logger.debug("Message sent: %s -> %s", sender, receiver)
        return message.message_id

    def _detect_deadlock(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self.wait_for_graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for agent_id in self.agents:
            if agent_id not in visited:
                if dfs(agent_id):
                    return True
        return False

    def _resolve_deadlock(self):
        with self.lock:
            for agent_id in self.agents:
                if self.agent_states.get(agent_id) == "waiting":
                    self.agent_states[agent_id] = "idle"
                    self.wait_for_graph[agent_id].clear()
            logger.warning("Deadlock detected and resolved")

    def execute_agent(self, agent_id: str, context: dict) -> Any:
        agent = self.agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")
        with self.lock:
            self.agent_states[agent_id] = "running"
        try:
            result = agent.handler(context)
            self.results[agent_id] = result
            with self.lock:
                self.agent_states[agent_id] = "completed"
                self.wait_for_graph[agent_id].clear()
            return result
        except Exception as e:
            with self.lock:
                self.agent_states[agent_id] = "failed"
            logger.error("Agent %s failed: %s", agent_id, e)
            raise

    def run_pipeline(self, task: dict, pipeline: List[str]) -> dict:
        context = dict(task)
        for agent_id in pipeline:
            if self._detect_deadlock():
                self._resolve_deadlock()
            result = self.execute_agent(agent_id, context)
            context[f"{agent_id}_result"] = result
        return context

    def get_status(self) -> dict:
        return {
            "agents": {aid: {"state": self.agent_states.get(aid, "unknown"), "capabilities": a.capabilities} for aid, a in self.agents.items()},
            "deadlock_detected": self._detect_deadlock(),
            "pending_messages": len(self.message_queue.queue),
        }
