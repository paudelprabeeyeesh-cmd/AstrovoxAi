"""Admin dashboard for Astrovox."""

from __future__ import annotations


class AdminDashboard:
    """Admin dashboard view."""

    def __init__(self):
        self.page = "admin"
        self.routes = ["/admin", "/admin/users", "/admin/usage", "/admin/logs"]

    def render(self, context: dict | None = None) -> str:
        ctx = context or {}
        return "<html><body><h1>Astrovox Admin Dashboard</h1><p>Welcome, admin.</p></body></html>"

    def get_stats(self) -> dict:
        return {"users": 0, "models": 0, "requests": 0, "errors": 0}
