import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class MentalState:
    beliefs: Dict[str, Any]
    desires: List[str]
    intentions: List[str]
    certainty: Dict[str, float]
    owner: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SocialContext:
    agents: List[str]
    relationships: Dict[str, float]
    shared_goals: List[str]
    history: List[Dict[str, Any]] = field(default_factory=list)


class TheoryOfMind:
    def __init__(self, agent_id: str, max_agents: int = 8):
        self.agent_id = agent_id
        self.max_agents = max_agents
        self._modeled_agents: Dict[str, MentalState] = {}
        self._inference_history: List[Dict[str, Any]] = []

    def model_agent(self, agent_id: str, observed_actions: List[Any], context: Dict[str, Any]) -> MentalState:
        beliefs = self._infer_beliefs(observed_actions, context)
        desires = self._infer_desires(observed_actions, beliefs)
        intentions = self._infer_intentions(observed_actions, desires)
        certainty = {b: 0.5 + 0.5 * np.random.random() for b in beliefs}
        state = MentalState(
            beliefs=beliefs,
            desires=desires,
            intentions=intentions,
            certainty=certainty,
            owner=agent_id,
        )
        if agent_id in self._modeled_agents:
            state = self._merge_states(self._modeled_agents[agent_id], state)
        self._modeled_agents[agent_id] = state
        self._inference_history.append({
            "agent": agent_id,
            "timestamp": time.time(),
            "beliefs": list(beliefs.keys()),
        })
        return state

    def _infer_beliefs(self, actions: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
        beliefs = {}
        for action in actions:
            if isinstance(action, dict) and "belief" in action:
                beliefs[action["belief"]] = action.get("confidence", 0.5)
            elif isinstance(action, str):
                beliefs[action] = 0.3
        return beliefs

    def _infer_desires(self, actions: List[Any], beliefs: Dict[str, Any]) -> List[str]:
        desires = []
        for belief_key in beliefs.keys():
            if "want" in belief_key.lower() or "goal" in belief_key.lower():
                desires.append(belief_key)
        if not desires and actions:
            desires.append(str(actions[-1])[:30])
        return desires

    def _infer_intentions(self, actions: List[Any], desires: List[str]) -> List[str]:
        intentions = []
        for action in actions[-3:]:
            if isinstance(action, str):
                intentions.append(action[:30])
        return intentions

    def _merge_states(self, old_state: MentalState, new_state: MentalState) -> MentalState:
        merged_beliefs = {**old_state.beliefs}
        for key, value in new_state.beliefs.items():
            if key in merged_beliefs:
                merged_beliefs[key] = 0.7 * merged_beliefs[key] + 0.3 * value
            else:
                merged_beliefs[key] = value
        merged_certainty = {**old_state.certainty}
        for key, value in new_state.certainty.items():
            merged_certainty[key] = max(merged_certainty.get(key, 0), value)
        return MentalState(
            beliefs=merged_beliefs,
            desires=list(set(old_state.desires + new_state.desires)),
            intentions=new_state.intentions,
            certainty=merged_certainty,
            owner=new_state.owner,
        )

    def predict_action(self, agent_id: str) -> Optional[str]:
        if agent_id not in self._modeled_agents:
            return None
        state = self._modeled_agents[agent_id]
        if state.intentions:
            return state.intentions[-1]
        return None

    def get_agent_model(self, agent_id: str) -> Optional[MentalState]:
        return self._modeled_agents.get(agent_id)


class EmpathyModel:
    def __init__(self, resonance_decay: float = 0.05):
        self.resonance_decay = resonance_decay
        self._emotional_resonance: Dict[str, float] = {}
        self._empathy_log: List[Dict[str, Any]] = []

    def resonate(self, target_state: EmotionState, source: str) -> float:
        resonance = target_state.intensity * (1.0 - self.resonance_decay)
        self._emotional_resonance[source] = resonance
        self._empathy_log.append({
            "source": source,
            "resonance": resonance,
            "target_valence": target_state.valence,
            "timestamp": time.time(),
        })
        return resonance

    def cognitive_empathy(self, mental_state: MentalState) -> Dict[str, Any]:
        perspective = {
            "beliefs": list(mental_state.beliefs.keys()),
            "desires": mental_state.desires,
            "intentions": mental_state.intentions,
            "certainty": np.mean(list(mental_state.certainty.values())) if mental_state.certainty else 0.0,
        }
        return perspective

    def affective_empathy(self, emotion_state: EmotionState) -> float:
        return emotion_state.intensity * np.abs(emotion_state.valence)

    def get_empathy_score(self, source: str) -> float:
        return self._emotional_resonance.get(source, 0.0)


class SocialCognitionSystem:
    def __init__(self, agent_id: str):
        self.theory_of_mind = TheoryOfMind(agent_id=agent_id)
        self.empathy_model = EmpathyModel()
        self.context = SocialContext(agents=[agent_id], relationships={}, shared_goals=[])
        self._interaction_log: List[Dict[str, Any]] = []

    def observe_interaction(self, agent_id: str, actions: List[Any], context: Dict[str, Any]) -> MentalState:
        state = self.theory_of_mind.model_agent(agent_id, actions, context)
        self._interaction_log.append({
            "agent": agent_id,
            "actions": len(actions),
            "timestamp": time.time(),
        })
        if agent_id not in self.context.agents:
            self.context.agents.append(agent_id)
        return state

    def respond_empathetically(self, target_state: EmotionState, source: str) -> float:
        resonance = self.empathy_model.resonate(target_state, source)
        cognitive = self.empathy_model.cognitive_empathy(
            MentalState(beliefs={}, desires=[], intentions=[], certainty={}, owner=source)
        )
        return resonance * (1.0 + cognitive["certainty"])

    def get_social_summary(self) -> Dict[str, Any]:
        return {
            "modeled_agents": list(self.theory_of_mind._modeled_agents.keys()),
            "interactions": len(self._interaction_log),
            "agents": self.context.agents,
        }
