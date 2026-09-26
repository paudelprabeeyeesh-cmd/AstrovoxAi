from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MultiAgentCollaboration:
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.shared_context: Dict[str, Any] = {}

    def register(self, agent: Any) -> None:
        self.agents[agent.agent_id] = agent

    def broadcast(self, sender_id: str, message: Dict[str, Any]) -> None:
        for agent_id, agent in self.agents.items():
            if agent_id != sender_id:
                if hasattr(agent, "receive"):
                    agent.receive(message)
                logger.debug("Broadcast from %s to %s", sender_id, agent_id)

    def coordinate(self, task: str) -> Dict[str, Any]:
        results = {}
        for agent_id, agent in self.agents.items():
            if hasattr(agent, "run"):
                results[agent_id] = agent.run(task, self.shared_context)
        return results

    def share_context(self, key: str, value: Any) -> None:
        self.shared_context[key] = value
