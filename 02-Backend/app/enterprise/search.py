"""Enterprise Search — global search across all resources."""

from typing import Optional
from dataclasses import dataclass, field

from .service import org_service


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    type: str  # conversation, document, memory, task, agent, user
    title: str
    content: str
    score: float = 0.0
    metadata: dict = field(default_factory=dict)


class EnterpriseSearch:
    """Search across all enterprise resources."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def search(
        self,
        query: str,
        organization_id: str = "",
        workspace_id: str = "",
        resource_type: str = "",
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search across all accessible resources."""
        results = []
        query_lower = query.lower()

        # Search workspaces
        if not resource_type or resource_type == "workspace":
            workspaces = org_service.get_user_workspaces(self.user_id, organization_id)
            for ws in workspaces:
                if query_lower in ws.name.lower() or query_lower in ws.description.lower():
                    score = 1.0 if query_lower == ws.name.lower() else 0.5
                    results.append(SearchResult(
                        id=ws.id,
                        type="workspace",
                        title=ws.name,
                        content=ws.description,
                        score=score,
                        metadata={"type": ws.type, "organization_id": ws.organization_id},
                    ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def search_workspaces(self, query: str, organization_id: str) -> list[SearchResult]:
        """Search workspaces only."""
        return self.search(query, organization_id, resource_type="workspace")
