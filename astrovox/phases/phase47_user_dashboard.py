"""User dashboard for Astrovox."""

from __future__ import annotations


class UserDashboard:
    """User dashboard view."""

    def __init__(self):
        self.page = "user"
        self.routes = ["/user", "/user/projects", "/user/usage", "/user/settings"]

    def render(self, context: dict | None = None) -> str:
        ctx = context or {}
        return f"<html><body><h1>Astrovox User Dashboard</h1><p>Welcome, user.</p></body></html>"

    def get_summary(self) -> dict:
        return {"projects": 0, "runs": 0, "models": 0}
