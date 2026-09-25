import requests
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    role: str
    content: str
    timestamp: Optional[str] = None

@dataclass
class Conversation:
    id: str
    title: str
    messages: List[Message]
    model: str = "gpt-4"
    created_at: Optional[str] = None

class AstrovoxClient:
    def __init__(self, api_key: str, base_url: str = "https://api.astrovox.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def send_message(self, conversation_id: str, message: str, model: str = "gpt-4") -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/chat/message",
            json={
                'conversation_id': conversation_id,
                'message': message,
                'model': model
            }
        )
        response.raise_for_status()
        return response.json()

    def create_conversation(self, title: str = "New Conversation", model: str = "gpt-4") -> Conversation:
        response = self.session.post(
            f"{self.base_url}/conversations",
            json={'title': title, 'model': model}
        )
        response.raise_for_status()
        data = response.json()
        return Conversation(
            id=data['id'],
            title=data['title'],
            messages=[],
            model=data.get('model', model),
            created_at=data.get('created_at')
        )

    def list_conversations(self) -> List[Conversation]:
        response = self.session.get(f"{self.base_url}/conversations")
        response.raise_for_status()
        data = response.json()
        return [
            Conversation(
                id=c['id'],
                title=c['title'],
                messages=[],
                model=c.get('model', 'gpt-4'),
                created_at=c.get('created_at')
            )
            for c in data
        ]

    def stream_message(self, conversation_id: str, message: str, model: str = "gpt-4"):
        response = self.session.post(
            f"{self.base_url}/chat/stream",
            json={'conversation_id': conversation_id, 'message': message, 'model': model},
            stream=True
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                yield line.decode('utf-8')

    def delete_conversation(self, conversation_id: str) -> bool:
        response = self.session.delete(f"{self.base_url}/conversations/{conversation_id}")
        return response.status_code == 204

    def health_check(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/health")
        return response.json()
