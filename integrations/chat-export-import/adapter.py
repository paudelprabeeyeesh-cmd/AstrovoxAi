import json
import csv
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)


class ChatExportFormat(Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"
    HTML = "html"
    PDF = "pdf"


@dataclass
class ChatExportOptions:
    format: ChatExportFormat = ChatExportFormat.JSON
    include_metadata: bool = True
    include_system_messages: bool = False
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    conversation_ids: Optional[List[str]] = None


@dataclass
class ChatImportResult:
    imported_count: int
    skipped_count: int
    errors: List[str] = field(default_factory=list)


class ChatExportImportAdapter:
    def __init__(self, api_client):
        self.api_client = api_client
        self._local_store: Dict[str, Dict[str, Any]] = {}

    def export_conversations(self, conversation_ids: List[str], options: ChatExportOptions = ChatExportOptions()) -> bytes:
        conversations = []
        for cid in conversation_ids:
            try:
                conv = self.api_client.get_conversation(cid)
                conversations.append(self._serialize_conversation(conv, options))
            except Exception as e:
                logger.error(f"Failed to fetch conversation {cid}: {e}")
        return self._render(conversations, options.format)

    def export_all(self, options: ChatExportOptions = ChatExportOptions()) -> bytes:
        try:
            all_conversations = self.api_client.list_conversations()
            cids = [c.id for c in all_conversations]
            if options.conversation_ids:
                cids = [cid for cid in cids if cid in options.conversation_ids]
            return self.export_conversations(cids, options)
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return b"[]"

    def import_from_json(self, data: bytes) -> ChatImportResult:
        try:
            payload = json.loads(data.decode('utf-8'))
        except json.JSONDecodeError as e:
            return ChatImportResult(imported_count=0, skipped_count=0, errors=[f"Invalid JSON: {e}"])
        return self._import_payload(payload)

    def import_from_csv(self, data: bytes) -> ChatImportResult:
        try:
            text = data.decode('utf-8')
            reader = csv.DictReader(StringIO(text))
            payload = []
            for row in reader:
                payload.append({"role": row.get("role", "user"), "content": row.get("content", ""), "timestamp": row.get("timestamp", "")})
            return self._import_payload({"messages": payload})
        except Exception as e:
            return ChatImportResult(imported_count=0, skipped_count=0, errors=[f"Invalid CSV: {e}"])

    def import_from_markdown(self, data: bytes) -> ChatImportResult:
        try:
            text = data.decode('utf-8')
            messages = []
            for line in text.splitlines():
                if line.startswith("## ") or line.startswith("# "):
                    continue
                if line.startswith("**User:**"):
                    messages.append({"role": "user", "content": line.replace("**User:**", "").strip()})
                elif line.startswith("**Assistant:**"):
                    messages.append({"role": "assistant", "content": line.replace("**Assistant:**", "").strip()})
            return self._import_payload({"messages": messages})
        except Exception as e:
            return ChatImportResult(imported_count=0, skipped_count=0, errors=[f"Invalid Markdown: {e}"])

    def _import_payload(self, payload: Dict[str, Any]) -> ChatImportResult:
        result = ChatImportResult(imported_count=0, skipped_count=0)
        messages = payload.get("messages", [])
        if not messages:
            result.errors.append("No messages found in payload")
            return result
        try:
            title = payload.get("title", f"Imported Chat {datetime.utcnow().isoformat()}")
            conv = self.api_client.create_conversation(title=title)
            for msg in messages:
                if msg.get("role") == "system":
                    continue
                try:
                    self.api_client.send_message(conv.id, msg.get("content", ""), msg.get("role", "user"))
                    result.imported_count += 1
                except Exception as e:
                    result.errors.append(f"Failed to import message: {e}")
                    result.skipped_count += 1
        except Exception as e:
            result.errors.append(f"Failed to create conversation: {e}")
        return result

    def _serialize_conversation(self, conv: Any, options: ChatExportOptions) -> Dict[str, Any]:
        serialized = {"id": conv.id, "title": conv.title, "model": conv.model, "created_at": getattr(conv, 'created_at', None)}
        if options.include_metadata:
            serialized["metadata"] = {"exported_at": datetime.utcnow().isoformat()}
        messages = []
        for msg in conv.messages:
            if not options.include_system_messages and msg.role == "system":
                continue
            messages.append({"role": msg.role, "content": msg.content, "timestamp": msg.timestamp})
        serialized["messages"] = messages
        return serialized

    def _render(self, conversations: List[Dict[str, Any]], format: ChatExportFormat) -> bytes:
        if format == ChatExportFormat.JSON:
            return json.dumps(conversations, indent=2).encode('utf-8')
        elif format == ChatExportFormat.CSV:
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=["conversation_id", "role", "content", "timestamp"])
            writer.writeheader()
            for conv in conversations:
                for msg in conv.get("messages", []):
                    writer.writerow({"conversation_id": conv["id"], "role": msg["role"], "content": msg["content"], "timestamp": msg.get("timestamp", "")})
            return output.getvalue().encode('utf-8')
        elif format == ChatExportFormat.MARKDOWN:
            lines = []
            for conv in conversations:
                lines.append(f"# {conv['title']}")
                lines.append("")
                for msg in conv.get("messages", []):
                    lines.append(f"**{msg['role'].capitalize()}:** {msg['content']}")
                    lines.append("")
            return "\n".join(lines).encode('utf-8')
        elif format == ChatExportFormat.HTML:
            parts = ["<html><body>"]
            for conv in conversations:
                parts.append(f"<h1>{conv['title']}</h1>")
                for msg in conv.get("messages", []):
                    parts.append(f"<p><strong>{msg['role']}:</strong> {msg['content']}</p>")
            parts.append("</body></html>")
            return "\n".join(parts).encode('utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")
