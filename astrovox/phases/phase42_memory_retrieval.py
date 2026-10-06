"""Memory retrieval API: unified search over stored memories."""

from __future__ import annotations

from astrovox.phases._shared.base import BaseStore
from astrovox.phases._shared.ranking import Ranker
from astrovox.phases._shared.retrieval_engine import RetrievalEngine


def search(store: BaseStore, query: str, top: int = 10,
           filters: dict | None = None) -> list[dict]:
    """Retrieve memories matching a query."""
    engine = RetrievalEngine()
    candidates = engine.search(store, query, limit=100)
    ranker = Ranker()
    ranked = ranker.rank(query, candidates, top=top)
    return ranked


def recall(store: BaseStore, entity: str, limit: int = 10) -> list[dict]:
    """Recall memories about an entity."""
    return store.search(entity, limit=limit)
