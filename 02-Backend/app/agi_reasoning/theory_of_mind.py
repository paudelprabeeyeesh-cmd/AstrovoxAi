import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BeliefState:
    beliefs: dict[str, float] = field(default_factory=dict)
    desires: list[str] = field(default_factory=list)
    intentions: list[str] = field(default_factory=list)
    knowledge: dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class InteractionRecord:
    agent_id: str
    action: str
    observation: str
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)


class TheoryOfMindService:
    def __init__(self) -> None:
        self._agents: dict[str, BeliefState] = {}
        self._history: list[InteractionRecord] = []
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register_agent(self, agent_id: str, initial_beliefs: dict[str, float] | None = None) -> dict[str, Any]:
        self._agents[agent_id] = BeliefState(beliefs=initial_beliefs or {})
        return {"agent_id": agent_id, "status": "registered"}

    def infer_state(self, agent_id: str, observations: list[str]) -> dict[str, Any]:
        state = self._agents.get(agent_id)
        if not state:
            state = BeliefState()
            self._agents[agent_id] = state

        updated_beliefs = self._update_beliefs(state, observations)
        inferred_desires = self._infer_desires(agent_id, updated_beliefs, observations)
        inferred_intentions = self._infer_intentions(agent_id, updated_beliefs, inferred_desires, observations)

        state.beliefs = updated_beliefs
        state.desires = inferred_desires
        state.intentions = inferred_intentions
        state.last_updated = time.time()

        for obs in observations:
            self._history.append(InteractionRecord(agent_id=agent_id, action="infer", observation=obs))

        return {
            "agent_id": agent_id,
            "beliefs": updated_beliefs,
            "desires": inferred_desires,
            "intentions": inferred_intentions,
            "confidence": self._estimate_confidence(updated_beliefs),
        }

    def record_interaction(self, agent_id: str, action: str, observation: str, context: dict[str, Any] | None = None) -> None:
        record = InteractionRecord(agent_id=agent_id, action=action, observation=observation, context=context or {})
        self._history.append(record)
        logger.debug("Recorded interaction for %s: %s", agent_id, action)

    def predict_action(self, agent_id: str, situation: str) -> dict[str, Any]:
        state = self._agents.get(agent_id)
        if not state:
            return {"agent_id": agent_id, "prediction": "unknown", "confidence": 0.0}

        try:
            prompt = (
                "Given the agent's current mental state and a new situation, predict the most likely action. "
                "Return JSON with keys: action (string), confidence (float 0-1), reasoning (string).\n"
                f"Agent beliefs: {state.beliefs}\nDesires: {state.desires}\nIntentions: {state.intentions}\n"
                f"Situation: {situation}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return {
                "agent_id": agent_id,
                "prediction": data.get("action", "unknown"),
                "confidence": float(data.get("confidence", 0.0)),
                "reasoning": data.get("reasoning", ""),
            }
        except Exception as exc:
            logger.error("Action prediction failed: %s", exc)
            return {"agent_id": agent_id, "prediction": "unknown", "confidence": 0.0, "error": str(exc)}

    def simulate_interaction(self, agent_id: str, scenario: str) -> dict[str, Any]:
        state = self._agents.get(agent_id)
        if not state:
            return {"agent_id": agent_id, "simulation": "unknown", "confidence": 0.0}

        try:
            prompt = (
                "Simulate how the agent would respond in the given scenario based on their mental state. "
                "Return JSON with keys: response (string), confidence (float 0-1), mental_process (string).\n"
                f"Agent beliefs: {state.beliefs}\nDesires: {state.desires}\nIntentions: {state.intentions}\n"
                f"Scenario: {scenario}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return {
                "agent_id": agent_id,
                "simulation": data.get("response", ""),
                "confidence": float(data.get("confidence", 0.0)),
                "mental_process": data.get("mental_process", ""),
            }
        except Exception as exc:
            logger.error("Simulation failed: %s", exc)
            return {"agent_id": agent_id, "simulation": "unknown", "confidence": 0.0, "error": str(exc)}

    def get_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        state = self._agents.get(agent_id)
        if not state:
            return None
        return {
            "agent_id": agent_id,
            "beliefs": state.beliefs,
            "desires": state.desires,
            "intentions": state.intentions,
            "knowledge": state.knowledge,
            "last_updated": state.last_updated,
        }

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def _update_beliefs(self, state: BeliefState, observations: list[str]) -> dict[str, float]:
        updated = dict(state.beliefs)
        for obs in observations:
            try:
                prompt = (
                    "Update the agent's beliefs based on the new observation. "
                    "Return a JSON object mapping belief names to updated confidence values (0.0-1.0).\n"
                    f"Current beliefs: {updated}\nObservation: {obs}"
                )
                client = self._get_client()
                response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                import json
                content = response.choices[0].message.content or "{}"
                changes = json.loads(content)
                for belief, confidence in changes.items():
                    updated[belief] = max(0.0, min(1.0, float(confidence)))
            except Exception as exc:
                logger.error("Belief update failed: %s", exc)
        return updated

    def _infer_desires(self, agent_id: str, beliefs: dict[str, float], observations: list[str]) -> list[str]:
        try:
            prompt = (
                "Infer the agent's desires (high-level goals) from their beliefs and recent observations. "
                "Return a JSON list of desire strings.\n"
                f"Beliefs: {beliefs}\nObservations: {observations}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "[]"
            return [d for d in json.loads(content) if isinstance(d, str)]
        except Exception as exc:
            logger.error("Desire inference failed: %s", exc)
            return []

    def _infer_intentions(self, agent_id: str, beliefs: dict[str, float], desires: list[str], observations: list[str]) -> list[str]:
        try:
            prompt = (
                "Infer the agent's immediate intentions (planned actions) from their beliefs, desires, and recent observations. "
                "Return a JSON list of intention strings.\n"
                f"Beliefs: {beliefs}\nDesires: {desires}\nObservations: {observations}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "[]"
            return [i for i in json.loads(content) if isinstance(i, str)]
        except Exception as exc:
            logger.error("Intention inference failed: %s", exc)
            return []

    def _estimate_confidence(self, beliefs: dict[str, float]) -> float:
        if not beliefs:
            return 0.0
        return round(sum(beliefs.values()) / len(beliefs), 4)
