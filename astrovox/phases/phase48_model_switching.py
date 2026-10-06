"""Runtime model switching."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelSwitcher:
    """Switch between model instances at runtime."""

    def __init__(self):
        self.current: str | None = None
        self.alternate: str | None = None
        self.history: list[str] = []
        self.switch_count = 0

    def switch_to(self, model_id: str) -> bool:
        if self.current == model_id:
            return True
        self.alternate = self.current
        self.current = model_id
        self.history.append(model_id)
        self.switch_count += 1
        return True

    def rollback(self) -> bool:
        if self.alternate is None:
            return False
        self.switch_to(self.alternate)
        return True

    def get_current(self) -> str | None:
        return self.current

    def get_alternate(self) -> str | None:
        return self.alternate

    def history(self, limit: int = 10) -> list[str]:
        return self.history[-limit:]

    def stats(self) -> dict:
        return {"current": self.current, "alternate": self.alternate,
                "switch_count": self.switch_count, "history_length": len(self.history)}
