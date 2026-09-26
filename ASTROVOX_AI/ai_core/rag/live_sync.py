"""Live document synchronization for RAG pipelines."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncEvent:
    event_type: str
    document_id: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LiveDocumentSync:
    """Live document synchronization with polling, webhooks, and change detection."""

    def __init__(self, poll_interval: float = 60.0):
        self.poll_interval = poll_interval
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._handlers: Dict[str, List[Callable[[SyncEvent], None]]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_document(self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            self._documents[document_id] = {
                "content": content,
                "metadata": metadata or {},
                "last_sync": datetime.now().isoformat(),
                "version": 1,
            }

    def update_document(self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if document_id not in self._documents:
                self.register_document(document_id, content, metadata)
                return
            old = self._documents[document_id]
            old["content"] = content
            old["metadata"] = {**old["metadata"], **(metadata or {})}
            old["last_sync"] = datetime.now().isoformat()
            old["version"] += 1
            event = SyncEvent(event_type="update", document_id=document_id, timestamp=old["last_sync"], metadata=old["metadata"])
            self._dispatch(event)

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            self._documents.pop(document_id, None)
            event = SyncEvent(event_type="delete", document_id=document_id, timestamp=datetime.now().isoformat())
            self._dispatch(event)

    def on_event(self, event_type: str, handler: Callable[[SyncEvent], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def start_polling(self, source: Callable[[], List[Dict[str, Any]]]) -> None:
        self._running = True

        def _poll():
            while self._running:
                try:
                    changes = source()
                    for change in changes:
                        doc_id = change.get("id", "")
                        content = change.get("content", "")
                        self.update_document(doc_id, content, change.get("metadata"))
                except Exception as exc:
                    logger.warning("Live sync poll failed: %s", exc)

        self._thread = threading.Thread(target=_poll, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._documents.get(document_id)

    def list_documents(self) -> List[str]:
        with self._lock:
            return list(self._documents.keys())

    def _dispatch(self, event: SyncEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as exc:
                logger.warning("Sync handler failed: %s", exc)
