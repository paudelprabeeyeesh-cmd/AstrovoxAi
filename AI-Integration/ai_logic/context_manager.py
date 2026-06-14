"""Context manager for Astravox AI memory and history preparation."""
from typing import Dict, List, Optional


def extract_recent_turns(history: Optional[List[Dict[str, str]]], max_turns: int = 12) -> List[Dict[str, str]]:
    if not history:
        return []
    return history[-max_turns:]


def summarize_conversation(history: Optional[List[Dict[str, str]]], max_lines: int = 20) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-max_lines:]:
        role = turn.get("role", "user")
        message = turn.get("message", "")
        lines.append(f"{role.capitalize()}: {message}")
    return "\n".join(lines)
