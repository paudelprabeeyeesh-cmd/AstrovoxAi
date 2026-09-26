from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class ModelRoute:
    model_id: str
    path: str
    allowed_orgs: List[str]


class AIGateway:
    def __init__(self):
        self.routes: Dict[str, ModelRoute] = {}

    def add_route(self, route: ModelRoute) -> None:
        self.routes[route.path] = route

    def route_request(self, path: str, org_id: str) -> ModelRoute:
        route = self.routes.get(path)
        if not route or org_id not in route.allowed_orgs:
            raise PermissionError("Access denied")
        return route
