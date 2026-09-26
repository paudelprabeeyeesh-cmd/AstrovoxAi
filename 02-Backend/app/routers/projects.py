import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


@router.post("/projects")
async def create_project(name: str, instructions: str = "", user_id: str = Depends(require_verified_email)):
    project_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO projects (id, user_id, name, instructions, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, user_id, name, instructions, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": project_id, "name": name, "instructions": instructions}


@router.get("/projects")
async def list_projects(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, instructions, created_at FROM projects WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, instructions, created_at FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.post("/projects/{project_id}/files")
async def add_project_file(project_id: str, filename: str, content: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        project = conn.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
        ).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        file_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO project_files (id, project_id, filename, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (file_id, project_id, filename, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"id": file_id, "filename": filename}


@router.get("/projects/{project_id}/files")
async def list_project_files(project_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        project = conn.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id)
        ).fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        rows = conn.execute(
            "SELECT id, filename, created_at FROM project_files WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
