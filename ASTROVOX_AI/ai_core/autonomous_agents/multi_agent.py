from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


class WorldModel:
    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

    def update(self, observation: Dict[str, Any]) -> None:
        self.state.update(observation)
        self.history.append({'timestamp': __import__('datetime').datetime.utcnow().isoformat(), **observation})

    def predict(self, action: Dict[str, Any]) -> Dict[str, Any]:
        predicted = dict(self.state)
        predicted['predicted_action'] = action
        return predicted

    def get_state(self) -> Dict[str, Any]:
        return dict(self.state)


class Agent:
    def __init__(self, agent_id: str, runtime: Any):
        self.agent_id = agent_id
        self.runtime = runtime
        self.world_model = WorldModel()
        self.status = 'idle'

    def perceive(self, observation: Dict[str, Any]) -> None:
        self.world_model.update(observation)

    def decide(self) -> Dict[str, Any]:
        state = self.world_model.get_state()
        return {'action': 'noop', 'reason': 'default policy'}

    def act(self, action: Dict[str, Any]) -> Any:
        if not self.runtime.safety_check(str(action)):
            logger.warning("Agent %s blocked unsafe action: %s", self.agent_id, action)
            return {"error": "unsafe action blocked"}
        self.status = 'acting'
        result = self.runtime._execute_step(str(action.get('action', '')))
        self.status = 'idle'
        return result

    def step(self, observation: Dict[str, Any]) -> Any:
        self.perceive(observation)
        action = self.decide()
        return self.act(action)


class MultiAgentOrchestrator:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self.agents[agent.agent_id] = agent

    def handoff(self, from_id: str, to_id: str, context: Dict[str, Any]) -> bool:
        if from_id in self.agents and to_id in self.agents:
            self.agents[to_id].perceive(context)
            logger.info("Handed off context from %s to %s", from_id, to_id)
            return True
        return False

    def run_round(self, task: str) -> Dict[str, Any]:
        results = {}
        for agent_id, agent in self.agents.items():
            results[agent_id] = agent.run(task, results)
        return results
