from typing import Any, Callable, List, Optional


class LivelockDetector:
    def __init__(self, progress_fn: Optional[Callable[[Any], bool]] = None):
        self.progress_fn = progress_fn or self._default_progress
        self.history: List[Any] = []
        self.livelock_detected: bool = False
        self.stable_rounds: int = 0
        self.max_stable_rounds: int = 5

    @staticmethod
    def _default_progress(state: Any) -> bool:
        return True

    def observe(self, state: Any) -> None:
        self.history.append(state)
        if len(self.history) >= 2:
            if not self.progress_fn(state):
                self.stable_rounds += 1
            else:
                self.stable_rounds = 0
        self.livelock_detected = self.stable_rounds >= self.max_stable_rounds

    def reset(self) -> None:
        self.history = []
        self.livelock_detected = False
        self.stable_rounds = 0
