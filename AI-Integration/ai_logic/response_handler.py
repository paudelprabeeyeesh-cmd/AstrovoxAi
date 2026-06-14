import os
import re
from typing import List, Optional


def _load_system_prompt() -> Optional[str]:
	"""Attempt to load the canonical system prompt from the prompts directory."""
	base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	paths = [
		os.path.join(base, "prompts", "system_prompt.txt"),
		os.path.join(base, "prompts", "system_prompt.md"),
	]
	for p in paths:
		if os.path.exists(p):
			try:
				with open(p, "r", encoding="utf-8") as fh:
					return fh.read()
			except Exception:
				return None
	return None


def clean_text(s: str, max_len: int = 30000) -> str:
	"""Sanitize AI output: strip control characters and trim length."""
	if s is None:
		return ""
	# Remove non-printable control characters except newlines and tabs
	s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", "", str(s))
	s = s.strip()
	if len(s) > max_len:
		s = s[:max_len] + "\n\n[Truncated]"
	return s


def format_response(response: str) -> str:
	"""Public formatter used by the backend to produce stable, clean responses."""
	cleaned = clean_text(response)
	# Collapse repeated whitespace
	cleaned = re.sub(r"\s{2,}", " ", cleaned)
	return cleaned


def assemble_prompt(user_message: str, history: Optional[List[dict]] = None) -> str:
	"""Compose a final prompt string including system prompt and recent history.

	History is a list of dicts with keys: role ('user'|'assistant'), 'message'.
	Keep this function deterministic and safe for logging.
	"""
	sys_prompt = _load_system_prompt() or "You are an assistant."
	lines = [sys_prompt, "", "Conversation:"]
	if history:
		for turn in history[-20:]:
			role = turn.get("role", "user")
			msg = turn.get("message") or turn.get("Astravox") or turn.get("response") or ""
			prefix = "User:" if role == "user" else "Assistant:"
			lines.append(f"{prefix} {msg}")
	lines.append(f"User: {user_message}")
	lines.append("Assistant:")
	return "\n".join(lines)
