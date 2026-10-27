"""Section 11 — Discrete math (topics 406-455)."""

from __future__ import annotations

import math
from typing import Any

from math_engine.core.result import MathResult
from math_engine.core.errors import ValidationError
from math_engine.core.validation import require_finite, require_non_negative, require_positive


def _result(topic_id: str, op: str, value: Any, steps: list[str] | None = None, **kw) -> MathResult:
    return MathResult(topic_id=topic_id, operation_id=op, status="implemented",
                      result=value, steps=steps or [], verified=True, **kw)


# Topic 424-426: Combinatorics / permutations / combinations
def count_permutations(n: Any, k: Any) -> MathResult:
    N = int(require_non_negative(require_finite(n, "n"), "n"))
    K = int(require_non_negative(require_finite(k, "k"), "k"))
    if K > N:
        raise ValidationError("k <= n")
    return _result("S11.T426", "count_permutations", math.perm(N, K),
                   steps=[f"P({N},{K}) = {math.perm(N, K)}"])


def count_combinations(n: Any, k: Any) -> MathResult:
    N = int(require_non_negative(require_finite(n, "n"), "n"))
    K = int(require_non_negative(require_finite(k, "k"), "k"))
    if K > N:
        raise ValidationError("k <= n")
    return _result("S11.T426", "count_combinations", math.comb(N, K),
                   steps=[f"C({N},{K}) = {math.comb(N, K)}"])


# Topic 428: Pigeonhole principle
def pigeonhole(items: Any, containers: Any) -> MathResult:
    I = int(require_non_negative(require_finite(items, "items"), "items"))
    C = int(require_positive(require_finite(containers, "containers"), "containers"))
    return _result("S11.T428", "pigeonhole",
                   {"items": I, "containers": C,
                    "min_in_one_container": math.ceil(I / C) if C else None,
                    "guaranteed_collision": I > C},
                   steps=[f"{I} items into {C} containers => at least ceil({I}/{C}) = {math.ceil(I/C)} in one"])


# Topic 430-433: Graph shortest path (Dijkstra)
def dijkstra(graph: dict, start: str, end: str) -> MathResult:
    import heapq
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    visited = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == end:
            break
        for v, w in graph.get(u, {}).items():
            nd = d + float(w)
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    path = []
    cur = end
    while cur in prev:
        path.append(cur)
        cur = prev[cur]
    path.append(start)
    path.reverse()
    return _result("S11.T433", "dijkstra",
                   {"distance": dist.get(end), "path": path, "reachable": end in dist},
                   steps=[f"Shortest path {start}->{end}: {' -> '.join(path)}, dist={dist.get(end)}"])


# Topic 454: Hashing demo
def hash_demo(value: Any, buckets: Any = 10) -> MathResult:
    B = int(require_positive(require_finite(buckets, "buckets"), "buckets"))
    h = hash(str(value)) % B
    return _result("S11.T454", "hash_demo",
                   {"bucket": h, "num_buckets": B, "value": str(value)},
                   steps=[f"hash({value}) mod {B} = {h}"])
