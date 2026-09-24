"""
Workflow orchestration with DAG execution.

Manages task graphs, resolves dependencies, and executes workflows.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


class TaskResult:
    def __init__(self, status: TaskStatus, output: Any = None, error: Optional[str] = None) -> None:
        self.status = status
        self.output = output
        self.error = error


@dataclass
class Task:
    name: str
    fn: Callable[..., Any]
    deps: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    retries: int = 2
    backoff: float = 0.05
    timeout: float = 60.0


@dataclass
class DAG:
    tasks: List[Task]
    name: str = "workflow"

    def build_graph(self) -> Tuple[Dict[str, Task], Dict[str, Set[str]]]:
        node_map = {t.name: t for t in self.tasks}
        edges = {t.name: set(t.deps) for t in self.tasks}
        return node_map, edges


class DAGExecutor:
    def __init__(self, dag: DAG) -> None:
        self.dag = dag
        self._lock = threading.RLock()
        self._status: Dict[str, TaskStatus] = {}
        self._results: Dict[str, TaskResult] = {}
        self._node_map, self._edges = dag.build_graph()
        self._log: List[str] = []

    def execute(self) -> Dict[str, TaskResult]:
        self._status = {name: TaskStatus.PENDING for name in self._node_map}
        self._results = {}
        order = self._topological_sort()
        for name in order:
            self._execute_task(name)
        return dict(self._results)

    def _topological_sort(self) -> List[str]:
        in_degree = {name: len(deps) for name, deps in self._edges.items()}
        queue = [n for n, d in in_degree.items() if d == 0]
        order: List[str] = []
        while queue:
            name = queue.pop(0)
            order.append(name)
            for t in self._node_map.values():
                if name in t.deps:
                    in_degree[t.name] -= 1
                    if in_degree[t.name] == 0:
                        queue.append(t.name)
        remaining = [n for n in self._node_map if n not in order]
        return order + remaining

    def _execute_task(self, name: str) -> None:
        task = self._node_map[name]
        deps = self._edges[name]
        for d in deps:
            if d not in self._results or self._results[d].status != TaskStatus.COMPLETED:
                self._status[name] = TaskStatus.SKIPPED
                self._results[name] = TaskResult(status=TaskStatus.SKIPPED, error="missing dep")
                return
        self._status[name] = TaskStatus.RUNNING
        for attempt in range(task.retries + 1):
            try:
                output = task.fn(**dict(task.params, name=name))
                self._status[name] = TaskStatus.COMPLETED
                self._results[name] = TaskResult(status=TaskStatus.COMPLETED, output=output)
                return
            except Exception as exc:
                import time
                time.sleep(task.backoff * (attempt + 1))
        self._status[name] = TaskStatus.FAILED
        self._results[name] = TaskResult(status=TaskStatus.FAILED, error="max retries exceeded")

    def log(self) -> List[str]:
        return list(self._log)

    def status(self) -> Dict[str, TaskStatus]:
        return dict(self._status)


class WorkflowEngine:
    def __init__(self) -> None:
        self._dags: Dict[str, DAG] = {}
        self._executions: Dict[str, DAGExecutor] = {}

    def register(self, dag: DAG) -> None:
        self._dags[dag.name] = dag

    def run(self, name: str) -> Dict[str, TaskResult]:
        dag = self._dags[name]
        executor = DAGExecutor(dag)
        self._executions[name] = executor
        return executor.execute()

    def status(self, name: str) -> Dict[str, TaskStatus]:
        return dict(self._executions[name]._status)
