import uuid
from datetime import datetime

from .database import get_db
from .schemas import TemplateCreate, TemplateOut


def create_template(user_id: str, data: TemplateCreate) -> TemplateOut:
    tpl_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO templates (id, user_id, name, prompt, variables) VALUES (?, ?, ?, ?, ?)",
            (tpl_id, user_id, data.name, data.prompt, data.variables),
        )
        conn.commit()
    return get_template(tpl_id)


def get_template(tpl_id: str) -> TemplateOut:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, prompt, variables, created_at FROM templates WHERE id = ?",
            (tpl_id,),
        ).fetchone()
        if not row:
            raise ValueError("Template not found")
        return TemplateOut(
            id=row["id"],
            name=row["name"],
            prompt=row["prompt"],
            variables=row["variables"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_templates(user_id: str) -> list[TemplateOut]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, prompt, variables, created_at FROM templates WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [
            TemplateOut(
                id=r["id"],
                name=r["name"],
                prompt=r["prompt"],
                variables=r["variables"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]


def update_template(tpl_id: str, user_id: str, data: TemplateCreate) -> TemplateOut:
    with get_db() as conn:
        conn.execute(
            "UPDATE templates SET name = ?, prompt = ?, variables = ? WHERE id = ? AND user_id = ?",
            (data.name, data.prompt, data.variables, tpl_id, user_id),
        )
        conn.commit()
    return get_template(tpl_id)


def delete_template(tpl_id: str, user_id: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM templates WHERE id = ? AND user_id = ?", (tpl_id, user_id)
        )
        conn.commit()
