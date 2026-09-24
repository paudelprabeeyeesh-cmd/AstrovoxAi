"""
Projects - product_polish

Manage projects and their associated files.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Project:
    id: str
    name: str
    instructions: str = ""
    created_at: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "instructions": self.instructions,
            "created_at": self.created_at,
            "meta": self.meta,
        }


@dataclass
class ProjectFile:
    id: str
    project_id: str
    filename: str
    content: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "filename": self.filename,
            "content": self.content,
            "created_at": self.created_at,
        }


class Projects:
    def __init__(self):
        self._projects: Dict[str, Project] = {}
        self._files: Dict[str, Dict[str, ProjectFile]] = {}

    def create(self, name: str, instructions: str = "", meta: Optional[Dict[str, Any]] = None) -> Project:
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name=name, instructions=instructions, meta=meta or {})
        self._projects[project_id] = project
        self._files[project_id] = {}
        return project

    def get(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def list_projects(self) -> List[Project]:
        return sorted(self._projects.values(), key=lambda p: p.created_at, reverse=True)

    def delete(self, project_id: str) -> bool:
        found = self._projects.pop(project_id, None) is not None
        self._files.pop(project_id, None)
        return found

    def add_file(self, project_id: str, filename: str, content: str) -> Optional[ProjectFile]:
        if project_id not in self._projects:
            return None
        file_id = str(uuid.uuid4())
        pf = ProjectFile(id=file_id, project_id=project_id, filename=filename, content=content)
        self._files[project_id][file_id] = pf
        return pf

    def list_files(self, project_id: str) -> List[ProjectFile]:
        files = self._files.get(project_id, {})
        return sorted(files.values(), key=lambda f: f.created_at, reverse=True)
