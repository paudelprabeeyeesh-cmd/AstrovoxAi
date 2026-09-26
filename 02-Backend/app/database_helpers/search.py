"""Full-text search helpers for PostgreSQL."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    id: Any
    rank: float
    headline: str | None = None


class FullTextSearch:
    """PostgreSQL full-text search utilities."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def search(
        self,
        table: str,
        columns: list[str],
        query: str,
        *,
        limit: int = 50,
        offset: int = 0,
        language: str = "english",
    ) -> list[SearchResult]:
        col_expr = " || ' ' || ".join(columns)
        sql = f"""
            SELECT id,
                   ts_rank(to_tsvector('{language}', {col_expr}), websearch_to_tsquery('{language}', :q)) AS rank
            FROM {table}
            WHERE to_tsvector('{language}', {col_expr}) @@ websearch_to_tsquery('{language}', :q)
            ORDER BY rank DESC
            LIMIT :limit OFFSET :offset
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"q": query, "limit": limit, "offset": offset}).fetchall()
        return [SearchResult(id=row.id, rank=float(row.rank)) for row in rows]

    def headline(self, table: str, column: str, query: str, id: Any, language: str = "english") -> str | None:
        sql = f"""
            SELECT ts_headline('{language}', {column}, websearch_to_tsquery('{language}', :q), 'StartSel=<mark>, StopSel=</mark>, MinWords=10, MaxWords=25') AS headline
            FROM {table}
            WHERE id = :id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"q": query, "id": id}).fetchone()
        return row.headline if row else None

    @staticmethod
    def create_tsvector_trigger(table: str, columns: list[str], language: str = "english") -> str:
        col_expr = " || ' ' || ".join(columns)
        return f"""
            CREATE OR REPLACE FUNCTION {table}_tsvector_update() RETURNS trigger AS $$
            BEGIN
              NEW.tsv := to_tsvector('{language}', {col_expr});
              RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
            DROP TRIGGER IF EXISTS {table}_tsvector_update ON {table};
            CREATE TRIGGER {table}_tsvector_update
              BEFORE INSERT OR UPDATE OF {', '.join(columns)} ON {table}
              FOR EACH ROW EXECUTE FUNCTION {table}_tsvector_update();
        """
