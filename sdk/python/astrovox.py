import requests
from typing import Optional, Dict, List, Any, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
import json
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: Optional[str] = None


@dataclass
class Conversation:
    id: str
    title: str
    messages: List[Message] = field(default_factory=list)
    model: str = "gpt-4"
    created_at: Optional[str] = None


@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None
    events: List[str] = field(default_factory=list)
    active: bool = True


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff_factor: float = 1.0
    retryable_statuses: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])


class AstrovoxClient:
    def __init__(self, api_key: str, base_url: str = "https://api.astrovox.ai/v1", timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self.timeout = timeout
        self.retry_policy = RetryPolicy()
        self._webhooks: List[WebhookConfig] = []

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        kwargs.setdefault('timeout', self.timeout)
        response = self.session.request(method, url, **kwargs)
        if response.status_code in self.retry_policy.retryable_statuses and self.retry_policy.max_retries > 0:
            return self._retry_request(method, path, response, kwargs)
        response.raise_for_status()
        return response

    def _retry_request(self, method: str, path: str, initial_response: requests.Response, kwargs: Dict) -> requests.Response:
        response = initial_response
        for attempt in range(self.retry_policy.max_retries):
            wait = self.retry_policy.backoff_factor * (2 ** attempt)
            logger.warning(f"Request failed with {response.status_code}, retrying in {wait}s...")
            time.sleep(wait)
            response = self.session.request(method, f"{self.base_url}{path}", **kwargs)
            if response.status_code not in self.retry_policy.retryable_statuses:
                response.raise_for_status()
                return response
        return response

    def send_message(self, conversation_id: str, message: str, model: str = "gpt-4") -> Dict[str, Any]:
        response = self._request("POST", "/chat/message", json={
            'conversation_id': conversation_id,
            'message': message,
            'model': model
        })
        return response.json()

    def stream_message(self, conversation_id: str, message: str, model: str = "gpt-4") -> Any:
        response = self._request("POST", "/chat/stream", json={
            'conversation_id': conversation_id,
            'message': message,
            'model': model
        }, stream=True)
        for line in response.iter_lines():
            if line:
                yield line.decode('utf-8')

    def create_conversation(self, title: str = "New Conversation", model: str = "gpt-4") -> Conversation:
        response = self._request("POST", "/conversations", json={'title': title, 'model': model})
        data = response.json()
        return Conversation(
            id=data['id'],
            title=data['title'],
            messages=[],
            model=data.get('model', model),
            created_at=data.get('created_at')
        )

    def list_conversations(self) -> List[Conversation]:
        response = self._request("GET", "/conversations")
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

    def get_conversation(self, conversation_id: str) -> Conversation:
        response = self._request("GET", f"/conversations/{conversation_id}")
        data = response.json()
        return Conversation(
            id=data['id'],
            title=data['title'],
            messages=[Message(**m) for m in data.get('messages', [])],
            model=data.get('model', 'gpt-4'),
            created_at=data.get('created_at')
        )

    def delete_conversation(self, conversation_id: str) -> bool:
        response = self._request("DELETE", f"/conversations/{conversation_id}")
        return response.status_code == 204

    def create_webhook(self, config: WebhookConfig) -> Dict[str, Any]:
        response = self._request("POST", "/webhooks", json={
            'url': config.url,
            'secret': config.secret,
            'events': config.events,
            'active': config.active
        })
        return response.json()

    def list_webhooks(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/webhooks")
        return response.json()

    def delete_webhook(self, webhook_id: str) -> bool:
        response = self._request("DELETE", f"/webhooks/{webhook_id}")
        return response.status_code == 204

    def export_conversation(self, conversation_id: str, format: str = "json") -> bytes:
        response = self._request("GET", f"/conversations/{conversation_id}/export", params={'format': format})
        return response.content

    def import_conversation(self, data: bytes, format: str = "json") -> Conversation:
        response = self._request("POST", "/conversations/import", data=data, headers={'Content-Type': f'application/{format}'})
        result = response.json()
        return Conversation(**result)

    def health_check(self) -> Dict[str, Any]:
        response = self._request("GET", "/health")
        return response.json()

    def authenticate_with_provider(self, provider: str, token: str) -> Dict[str, Any]:
        response = self._request("POST", "/auth/providers", json={'provider': provider, 'token': token})
        return response.json()

    def register_plugin(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        response = self._request("POST", "/plugins/register", json=manifest)
        return response.json()
