import uuid
from datetime import datetime

from .database import get_db
from .schemas import WorkflowCreate, WorkflowOut


def create_workflow(user_id: str, data: WorkflowCreate) -> WorkflowOut:
    wf_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO workflows (id, user_id, name, steps) VALUES (?, ?, ?, ?)",
            (wf_id, user_id, data.name, data.steps),
        )
        conn.commit()
    return WorkflowOut(
        id=wf_id, name=data.name, steps=data.steps, created_at=datetime.utcnow()
    )


def get_workflow(wf_id: str, user_id: str) -> WorkflowOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, steps, created_at FROM workflows WHERE id = ? AND user_id = ?",
            (wf_id, user_id),
        ).fetchone()
        if not row:
            raise ValueError("Workflow not found")
        return WorkflowOut(
            id=row["id"],
            name=row["name"],
            steps=row["steps"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_workflows(user_id: str) -> list[WorkflowOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, steps, created_at FROM workflows WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            WorkflowOut(
                id=r["id"],
                name=r["name"],
                steps=r["steps"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def delete_workflow(wf_id: str, user_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM workflows WHERE id = ? AND user_id = ?", (wf_id, user_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError("Workflow not found")
