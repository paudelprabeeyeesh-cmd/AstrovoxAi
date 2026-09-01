"""Global Scale — millions of users, multi-region, edge AI."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrafficRoute:
    """A traffic routing rule."""
    region: str
    weight: float
    is_active: bool = True


class GlobalScaleManager:
    """Manage global scaling."""

    def __init__(self):
        self._routes: list[TrafficRoute] = []

    def add_route(self, region: str, weight: float):
        self._routes.append(TrafficRoute(region=region, weight=weight))

    def get_routes(self) -> list:
        return [r for r in self._routes if r.is_active]

    def route_traffic(self) -> str:
        """Route traffic to a region based on weights."""
        import random
        routes = self.get_routes()
        if not routes:
            return "us-east-1"

        total = sum(r.weight for r in routes)
        rand = random.uniform(0, total)

        cumulative = 0
        for route in routes:
            cumulative += route.weight
            if rand <= cumulative:
                return route.region

        return routes[-1].region


global_scale = GlobalScaleManager()
