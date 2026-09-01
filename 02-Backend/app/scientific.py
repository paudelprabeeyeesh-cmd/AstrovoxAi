"""Scientific AI — research assistants, data analysis, experiment automation."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ResearchProject:
    """A research project."""
    id: str
    title: str
    description: str
    status: str = "active"
    created_at: float = 0.0
    datasets: list = field(default_factory=list)
    experiments: list = field(default_factory=list)

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class ScientificAI:
    """Scientific AI research platform."""

    def __init__(self):
        self._projects: dict[str, ResearchProject] = {}

    def create_project(self, title: str, description: str) -> ResearchProject:
        """Create a research project."""
        import secrets
        project = ResearchProject(
            id=secrets.token_hex(8),
            title=title,
            description=description,
        )
        self._projects[project.id] = project
        return project

    def add_dataset(self, project_id: str, dataset_name: str, data: dict):
        project = self._projects.get(project_id)
        if project:
            project.datasets.append({
                "name": dataset_name,
                "data": data,
                "added_at": time.time(),
            })

    def get_projects(self, status: str = None) -> list:
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return projects


scientific_ai = ScientificAI()
