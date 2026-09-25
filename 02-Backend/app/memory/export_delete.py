"""Memory export and deletion utilities."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import io
import csv
from dataclasses import dataclass


class MemoryExporter:
    @staticmethod
    def to_json(memories: List[Dict[str, Any]]) -> str:
        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "count": len(memories),
            "memories": memories,
        }
        return json.dumps(export_data, indent=2, default=str)

    @staticmethod
    def to_csv(memories: List[Dict[str, Any]]) -> str:
        if not memories:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=memories[0].keys())
        writer.writeheader()
        for memory in memories:
            writer.writerow({k: str(v) for k, v in memory.items()})
        return output.getvalue()

    @staticmethod
    def to_markdown(memories: List[Dict[str, Any]]) -> str:
        lines = ["# Memory Export", f"Exported at: {datetime.now(timezone.utc).isoformat()}", ""]
        for i, memory in enumerate(memories, 1):
            lines.append(f"## Memory {i}")
            for key, value in memory.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        return "\n".join(lines)


class MemoryDeleter:
    @staticmethod
    def soft_delete(memory: Dict[str, Any]) -> Dict[str, Any]:
        memory["deleted"] = True
        memory["deleted_at"] = datetime.now(timezone.utc).isoformat()
        return memory

    @staticmethod
    def hard_delete(memory_id: str, store: Any) -> bool:
        try:
            if hasattr(store, "delete"):
                store.delete(memory_id)
            return True
        except Exception:
            return False
