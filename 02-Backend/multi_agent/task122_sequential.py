from typing import Any, Callable, List, Optional


class SequentialOrchestrator:
    def __init__(self):
        self.tasks: List[Callable[[], Any]] = []
        self.results: List[Any] = []
        self.errors: List[Optional[str]] = []

    def add_task(self, func: Callable[[], Any]) -> None:
        self.tasks.append(func)

    def run(self, propagate_errors: bool = True) -> List[Any]:
        self.results = []
        self.errors = []
        for idx, func in enumerate(self.tasks):
            try:
                result = func()
                self.results.append(result)
                self.errors.append(None)
            except Exception as exc:
                self.results.append(None)
                self.errors.append(str(exc))
                if propagate_errors:
                    for j in range(idx + 1, len(self.tasks)):
                        self.tasks[j] = self._wrap_with_error_context(
                            self.tasks[j], idx
                        )
        return self.results

    @staticmethod
    def _wrap_with_error_context(func: Callable[[], Any], failed_index: int) -> Callable[[], Any]:
        def wrapper():
            raise RuntimeError(
                f"Task {failed_index} failed; subsequent task blocked by error propagation."
            )
        return wrapper
