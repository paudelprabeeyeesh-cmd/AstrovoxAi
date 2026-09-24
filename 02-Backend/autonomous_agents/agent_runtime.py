from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AgentState:
    id: str
    status: str = "idle"
    memory: Dict[str, Any] = field(default_factory=dict)
    step_count: int = 0
    last_error: Optional[str] = None


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None


class AgentRuntime:
    def __init__(self, max_steps: int = 100):
        self.max_steps = max_steps
        self.agents: Dict[str, AgentState] = {}
        self.history: List[ToolCall] = []
        self._counter = 0

    def spawn(self, initial_memory: Optional[Dict[str, Any]] = None) -> AgentState:
        self._counter += 1
        agent = AgentState(id=f"agent_{self._counter}", memory=initial_memory or {})
        self.agents[agent.id] = agent
        return agent

    def call_tool(self, agent_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        agent = self.agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent {agent_id} not found")
        call = ToolCall(tool_name=tool_name, arguments=dict(arguments))
        try:
            call.result = f"result:{tool_name}"
        except Exception as exc:
            call.error = str(exc)
            agent.last_error = call.error
        self.history.append(call)
        agent.step_count += 1
        if agent.step_count >= self.max_steps:
            agent.status = "exhausted"
        return call.result if call.error is None else None

    def get_state(self, agent_id: str) -> Optional[AgentState]:
        return self.agents.get(agent_id)

    def shutdown(self, agent_id: str) -> bool:
        agent = self.agents.pop(agent_id, None)
        if agent is not None:
            agent.status = "shutdown"
            return True
        return False
