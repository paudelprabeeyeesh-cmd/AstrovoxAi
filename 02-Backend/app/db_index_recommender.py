"""DB index recommendation helper."""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("astrovox.db_index")


class DBIndexRecommender:
    """Recommend database indexes based on query patterns."""

    def __init__(self) -> None:
        self._recommendations: list[dict] = []

    def analyze_query(self, query: str, plan: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        recommendations = []
        query_lower = query.lower()

        where_columns = self._extract_where_columns(query)
        join_columns = self._extract_join_columns(query)
        order_columns = self._extract_order_columns(query)
        group_columns = self._extract_group_columns(query)

        for col in where_columns:
            recommendations.append({
                "type": "index",
                "columns": [col],
                "reason": "Column used in WHERE clause",
                "priority": "high",
            })

        for col in join_columns:
            recommendations.append({
                "type": "index",
                "columns": [col],
                "reason": "Column used in JOIN condition",
                "priority": "high",
            })

        for col in order_columns:
            recommendations.append({
                "type": "index",
                "columns": [col],
                "reason": "Column used in ORDER BY",
                "priority": "medium",
            })

        for col in group_columns:
            recommendations.append({
                "type": "index",
                "columns": [col],
                "reason": "Column used in GROUP BY",
                "priority": "medium",
            })

        if plan:
            plan_analysis = self._analyze_plan(plan)
            recommendations.extend(plan_analysis)

        self._recommendations.extend(recommendations)
        return recommendations

    def get_recommendations(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._recommendations[-limit:]

    def clear(self) -> None:
        self._recommendations.clear()

    def _extract_where_columns(self, query: str) -> List[str]:
        columns = []
        match = re.search(r"where\s+(.+?)(?:\s+order\s+by|\s+group\s+by|\s+limit|\s+union|\s+intersect|\s+except|$)", query, re.IGNORECASE | re.DOTALL)
        if match:
            where_clause = match.group(1)
            columns = re.findall(r"(\w+)\s*(?:=|!=|<>|>=|<=|>|<|like|ilike|in\s*\()", where_clause, re.IGNORECASE)
        return list(set(columns))

    def _extract_join_columns(self, query: str) -> List[str]:
        columns = []
        matches = re.findall(r"join\s+\w+\s+(?:as\s+\w+\s+)?on\s+(.+?)(?:\s+join|\s+where|\s+group\s+by|\s+order\s+by|\s+limit|$)", query, re.IGNORECASE | re.DOTALL)
        for match in matches:
            columns.extend(re.findall(r"(\w+)\s*=", match))
        return list(set(columns))

    def _extract_order_columns(self, query: str) -> List[str]:
        columns = []
        match = re.search(r"order\s+by\s+(.+?)(?:\s+limit|\s+for|\s+offset|$)", query, re.IGNORECASE | re.DOTALL)
        if match:
            columns = re.findall(r"(\w+)", match.group(1))
        return list(set(columns))

    def _extract_group_columns(self, query: str) -> List[str]:
        columns = []
        match = re.search(r"group\s+by\s+(.+?)(?:\s+having|\s+order\s+by|\s+limit|$)", query, re.IGNORECASE | re.DOTALL)
        if match:
            columns = re.findall(r"(\w+)", match.group(1))
        return list(set(columns))

    def _analyze_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommendations = []
        plan_text = str(plan)
        if "Seq Scan" in plan_text:
            recommendations.append({
                "type": "index",
                "columns": [],
                "reason": "Sequential scan detected - consider adding an index",
                "priority": "high",
            })
        if "Sort" in plan_text:
            recommendations.append({
                "type": "config",
                "columns": [],
                "reason": "Sort operation detected - consider increasing work_mem",
                "priority": "low",
            })
        return recommendations


db_index_recommender = DBIndexRecommender()
