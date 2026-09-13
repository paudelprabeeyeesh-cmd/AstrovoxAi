import json
import logging
from typing import Optional
from app.services.rag import RAGService
from app.config import settings

logger = logging.getLogger(__name__)


class TenantIsolationChecker:
    def __init__(self, db_client):
        self.db = db_client
    
    def check_query_isolation(self, query: str, user_id: str, team_id: str = None) -> bool:
        if "user_id" in query and f"'{user_id}'" not in query:
            return False
        if team_id and "team_id" in query and f"'{team_id}'" not in query:
            return False
        return True
    
    def check_all_queries(self, user_id: str, team_id: str = None) -> list[str]:
        violations = []
        test_queries = [
            "SELECT * FROM conversations WHERE user_id = 'other_user'",
            "SELECT * FROM memories WHERE user_id != ?",
            "DELETE FROM conversations WHERE user_id = 'other_user'",
        ]
        
        for query in test_queries:
            if not self.check_query_isolation(query, user_id, team_id):
                violations.append(query)
        
        return violations
    
    def enforce_tenant_filter(self, query: str, user_id: str) -> str:
        if "WHERE" in query.upper() and "user_id" not in query:
            query += f" AND user_id = '{user_id}'"
        return query
