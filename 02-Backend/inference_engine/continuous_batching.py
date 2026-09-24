
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class RequestState(Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    PREEMPTED = "preempted"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass
class ScheduledRequest:
    request_id: str
    prompt_ids: List[int]
    max_new_tokens: int
    priority: int = 0
    arrival_time: float = 0.0
    state: RequestState = RequestState.WAITING
    generated_tokens: List[int] = field(default_factory=list)
    preempted_count: int = 0
    metadata: Dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return len(self.prompt_ids) + len(self.generated_tokens)

    @property
    def completed(self) -> bool:
        return len(self.generated_tokens) >= self.max_new_tokens


class ContinuousBatchScheduler:
    def __init__(self, max_active: int = 16, max_queue: int = 128,
                 max_preempted: int = 8, preempt_threshold: float = 0.5):
        self.max_active = max_active
        self.max_queue = max_queue
        self.max_preempted = max_preempted
        self.preempt_threshold = preempt_threshold
        self.active: Dict[str, ScheduledRequest] = {}
        self.waiting: List[ScheduledRequest] = []
        self.preempted: Dict[str, ScheduledRequest] = {}
        self.completed: Dict[str, ScheduledRequest] = {}
        self.rejected: Dict[str, ScheduledRequest] = {}
        self._step = 0

    def submit(self, req: ScheduledRequest) -> bool:
        req.arrival_time = self._step
        if len(self.active) < self.max_active:
            self._admit(req)
            return True
        if self.max_preempted > 0 and self.active:
            candidates = [(r.priority, r.arrival_time, r.preempted_count, r.request_id)
                          for r in self.active.values()]
            candidates.sort()
            lowest_priority, _, lowest_preempted, lowest_id = candidates[0]
            if lowest_priority < req.priority:
                self._preempt(lowest_id)
                self._admit(req)
                return True
        if len(self.waiting) < self.max_queue:
            req.state = RequestState.WAITING
            self.waiting.append(req)
            self._try_admit_from_queue()
            return True
        req.state = RequestState.REJECTED
        self.rejected[req.request_id] = req
        return False

    def _admit(self, req: ScheduledRequest):
        req.state = RequestState.ACTIVE
        self.active[req.request_id] = req

    def _preempt(self, req_id: str):
        req = self.active.pop(req_id, None)
        if req is None:
            return
        req.state = RequestState.PREEMPTED
        req.preempted_count += 1
        self.preempted[req_id] = req

    def _try_admit_from_queue(self):
        while len(self.active) < self.max_active and self.waiting:
            candidate = self._select_next_from_queue()
            if candidate is None:
                break
            self.waiting.remove(candidate)
            self._admit(candidate)

    def _select_next_from_queue(self) -> Optional[ScheduledRequest]:
        if not self.waiting:
            return None
        best = max(self.waiting, key=lambda r: (r.priority, -r.arrival_time))
        return best

    def step(self) -> Dict[str, List[str]]:
        self._step += 1
        events = {"completed": [], "preempted": [], "newly_active": []}
        to_complete = []
        for req_id, req in list(self.active.items()):
            req.generated_tokens.append(1)
            if req.completed:
                to_complete.append(req_id)
        for req_id in to_complete:
            req = self.active.pop(req_id)
            req.state = RequestState.COMPLETED
            self.completed[req_id] = req
            events["completed"].append(req_id)
            self._try_admit_from_queue()
        return events

    def preempt_lowest_priority(self, count: int = 1) -> List[str]:
        candidates = sorted(self.active.values(),
                            key=lambda r: (r.priority, r.arrival_time))
        preempted = []
        for req in candidates[:count]:
            req_id = req.request_id
            req = self.active.pop(req_id)
            req.state = RequestState.PREEMPTED
            self.preempted[req_id] = req
            preempted.append(req_id)
        return preempted

    def resume(self, req_id: str) -> bool:
        req = self.preempted.get(req_id)
        if req is None:
            return False
        if len(self.active) >= self.max_active:
            if self.max_preempted > 0 and self.active:
                candidates = sorted(self.active.values(),
                                    key=lambda r: (r.priority, r.arrival_time))
                lowest = candidates[0]
                self._preempt(lowest.request_id)
            else:
                return False
        self.preempted.pop(req_id)
        self._admit(req)
        return True

    def get_stats(self) -> Dict:
        return {
            "active": len(self.active),
            "queued": len(self.waiting),
            "preempted": len(self.preempted),
            "completed": len(self.completed),
            "rejected": len(self.rejected),
        }

    def get_request(self, req_id: str) -> Optional[ScheduledRequest]:
        for container in [self.active, self.waiting, self.preempted, self.completed, self.rejected]:
            if req_id in container:
                return container[req_id]
        return None
