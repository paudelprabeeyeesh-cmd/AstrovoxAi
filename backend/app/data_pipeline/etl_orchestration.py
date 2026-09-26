import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ETLTask:
    name: str
    extract: Callable
    transform: Callable
    load: Callable
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ETLOrchestratorConfig:
    max_parallel_tasks: int = 4
    retry_attempts: int = 3
    checkpoint_path: str = "./etl_checkpoints"


class ETLOrchestrator:
    def __init__(self, config: Optional[ETLOrchestratorConfig] = None):
        self.config = config or ETLOrchestratorConfig()
        self.tasks: Dict[str, ETLTask] = {}
        self.results: Dict[str, Any] = {}
        self.failed: Dict[str, Exception] = {}
        logger.info(
            "ETL orchestrator initialized: max_parallel=%d",
            self.config.max_parallel_tasks,
        )

    def register_task(self, task: ETLTask) -> None:
        self.tasks[task.name] = task
        logger.info("Registered ETL task: %s", task.name)

    def _topological_sort(self) -> List[ETLTask]:
        visited: set = set()
        order: List[ETLTask] = []

        def visit(task_name: str) -> None:
            if task_name in visited:
                return
            visited.add(task_name)
            task = self.tasks.get(task_name)
            if task:
                for dep in task.depends_on:
                    visit(dep)
                order.append(task)

        for name in self.tasks:
            visit(name)
        return order

    def _execute_task(self, task: ETLTask) -> Any:
        extracted = task.extract()
        transformed = task.transform(extracted)
        loaded = task.load(transformed)
        self.results[task.name] = loaded
        logger.info("ETL task %s completed", task.name)
        return loaded

    def run(self) -> Dict[str, Any]:
        sorted_tasks = self._topological_sort()
        for task in sorted_tasks:
            for attempt in range(self.config.retry_attempts):
                try:
                    self._execute_task(task)
                    break
                except Exception as exc:
                    logger.warning(
                        "ETL task %s failed on attempt %d: %s",
                        task.name,
                        attempt + 1,
                        exc,
                    )
                    if attempt == self.config.retry_attempts - 1:
                        self.failed[task.name] = exc
                        logger.error("ETL task %s failed after %d attempts", task.name, self.config.retry_attempts)
        return {
            "completed": list(self.results.keys()),
            "failed": list(self.failed.keys()),
            "results": self.results,
        }

    def run_parallel(self) -> Dict[str, Any]:
        sorted_tasks = self._topological_sort()
        completed: set = set()
        pending = {t.name: t for t in sorted_tasks}

        while pending:
            ready = []
            for name, task in list(pending.items()):
                if all(dep in completed for dep in task.depends_on):
                    ready.append(task)
            for task in ready:
                pending.pop(task.name, None)
            if not ready:
                break
            for task in ready:
                try:
                    self._execute_task(task)
                    completed.add(task.name)
                except Exception as exc:
                    self.failed[task.name] = exc
        return {
            "completed": list(self.results.keys()),
            "failed": list(self.failed.keys()),
            "results": self.results,
        }
