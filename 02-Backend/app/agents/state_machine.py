"""Agent state machine for lifecycle management."""

from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto


class AgentState(Enum):
    INITIALIZING = auto()
    IDLE = auto()
    THINKING = auto()
    ACTING = auto()
    WAITING = auto()
    COMPLETED = auto()
    FAILED = auto()
    STOPPED = auto()


@dataclass
class StateTransition:
    from_state: AgentState
    to_state: AgentState
    trigger: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentStateMachine:
    _transitions: Dict[str, StateTransition] = {}
    _current_states: Dict[str, AgentState] = {}

    VALID_TRANSITIONS = {
        AgentState.INITIALIZING: [AgentState.IDLE, AgentState.FAILED],
        AgentState.IDLE: [AgentState.THINKING, AgentState.STOPPED],
        AgentState.THINKING: [AgentState.ACTING, AgentState.IDLE, AgentState.FAILED],
        AgentState.ACTING: [AgentState.WAITING, AgentState.COMPLETED, AgentState.FAILED, AgentState.IDLE],
        AgentState.WAITING: [AgentState.THINKING, AgentState.IDLE],
        AgentState.COMPLETED: [AgentState.IDLE],
        AgentState.FAILED: [AgentState.IDLE],
        AgentState.STOPPED: [AgentState.INITIALIZING],
    }

    @classmethod
    def register_transition(cls, transition: StateTransition) -> None:
        cls._transitions[f"{transition.from_state.value}:{transition.trigger}"] = transition

    @classmethod
    def transition(cls, agent_id: str, trigger: str) -> bool:
        current_state = cls._current_states.get(agent_id, AgentState.INITIALIZING)
        key = f"{current_state.value}:{trigger}"
        transition = cls._transitions.get(key)
        if not transition:
            return False
        if transition.to_state not in cls.VALID_TRANSITIONS.get(current_state, []):
            return False
        cls._current_states[agent_id] = transition.to_state
        return True

    @classmethod
    def get_state(cls, agent_id: str) -> AgentState:
        return cls._current_states.get(agent_id, AgentState.INITIALIZING)

    @classmethod
    def set_state(cls, agent_id: str, state: AgentState) -> None:
        cls._current_states[agent_id] = state
