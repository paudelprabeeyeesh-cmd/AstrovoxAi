
import uuid
from datetime import datetime, timezone
from repositories.database.client import get_db

def create_team(owner_id: str, name: str) -> str:
    team_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO teams (id, owner_id, name) VALUES (?, ?, ?)", (team_id, owner_id, name))
        conn.execute("INSERT INTO team_members (id, team_id, user_id, role) VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), team_id, owner_id, "owner"))
        conn.commit()
    return team_id

def add_member(team_id: str, user_id: str, role: str = "member"):
    with get_db() as conn:
        conn.execute("INSERT INTO team_members (id, team_id, user_id, role) VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), team_id, user_id, role))
        conn.commit()

def invite_member(team_id: str, email: str, inviter_id: str) -> dict:
    invite_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute("INSERT INTO team_invitations (id, team_id, email, inviter_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (invite_id, team_id, email, inviter_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    return {"invite_id": invite_id, "team_id": team_id, "email": email}

def list_teams(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT t.id, t.name, t.created_at, tm.role FROM teams t JOIN team_members tm ON tm.team_id = t.id WHERE tm.user_id = ?", (user_id,)).fetchall()
        return [{"id": r["id"], "name": r["name"], "role": r["role"], "created_at": r["created_at"]} for r in rows]

def get_team(team_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT id, name, owner_id, created_at FROM teams WHERE id = ?", (team_id,)).fetchone()
        if not row: raise ValueError("Team not found")
        members = conn.execute("SELECT user_id, role FROM team_members WHERE team_id = ?", (team_id,)).fetchall()
        return {"id": row["id"], "name": row["name"], "owner_id": row["owner_id"], "created_at": row["created_at"], "members": [{"user_id": m["user_id"], "role": m["role"]} for m in members]}

def get_team_analytics(team_id: str) -> dict:
    with get_db() as conn:
        member_count = conn.execute("SELECT COUNT(*) as c FROM team_members WHERE team_id = ?", (team_id,)).fetchone()["c"]
    return {"team_id": team_id, "member_count": member_count}
