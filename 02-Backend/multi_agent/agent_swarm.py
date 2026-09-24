from typing import Any, Callable, Dict, List, Optional, Sequence


class Agent:
    def __init__(self, name: str, handler: Optional[Callable[[str], Any]] = None) -> None:
        self.name = name
        self.handler = handler or (lambda msg: f"{name}:{msg}")
        self.inbox: List[str] = []
        self.outbox: List[str] = []

    def receive(self, message: str) -> Any:
        self.inbox.append(message)
        return self.handler(message)

    def send(self, message: str) -> str:
        self.outbox.append(message)
        return message


class Swarm:
    def __init__(self) -> None:
        self.agents: Dict[str, Agent] = {}
        self.messages: List[Dict[str, Any]] = []

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def broadcast(self, source: str, message: str) -> List[Any]:
        results = []
        for name, agent in self.agents.items():
            if name != source:
                results.append(agent.receive(f"{source}->{name}:{message}"))
        self.messages.append({"source": source, "message": message, "recipients": list(self.agents.keys())})
        return results

    def send_to(self, source: str, target: str, message: str) -> Any:
        if target not in self.agents:
            raise ValueError(f"Target agent '{target}' not in swarm")
        result = self.agents[target].receive(f"{source}->{target}:{message}")
        self.messages.append({"source": source, "target": target, "message": message})
        return result

    def collective_output(self) -> Dict[str, List[str]]:
        return {name: agent.outbox for name, agent in self.agents.items()}
