from typing import Any, Callable, Dict, List, Optional, Sequence


class Message:
    def __init__(self, sender: str, recipient: str, payload: Any) -> None:
        self.sender = sender
        self.recipient = recipient
        self.payload = payload
        self.history: List[Dict[str, Any]] = [{"sender": sender, "recipient": recipient, "payload": payload}]

    def __repr__(self) -> str:
        return f"Message({self.sender}->{self.recipient}, {self.payload!r})"


class MessageRouter:
    def __init__(self) -> None:
        self.routes: Dict[str, List[str]] = {}
        self.queue: List[Message] = []

    def register(self, agent: str, destinations: Sequence[str]) -> None:
        self.routes[agent] = list(destinations)

    def send(self, sender: str, recipient: str, payload: Any) -> Message:
        message = Message(sender, recipient, payload)
        self.queue.append(message)
        return message

    def route(self, message: Message) -> List[Message]:
        forwarded: List[Message] = []
        destinations = self.routes.get(message.sender, [])
        for destination in destinations:
            if destination != message.recipient:
                new_message = Message(message.sender, destination, message.payload)
                new_message.history = list(message.history)
                forwarded.append(new_message)
                self.queue.append(new_message)
        message.history.append({"action": "routed", "from": message.sender})
        return forwarded

    def drain(self, recipient: str) -> List[Message]:
        incoming = [m for m in self.queue if m.recipient == recipient]
        self.queue = [m for m in self.queue if m.recipient != recipient]
        return incoming

    def pending(self) -> List[Message]:
        return list(self.queue)
