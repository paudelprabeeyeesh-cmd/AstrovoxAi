import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email, require_admin
from repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["plugins"])


@router.get("/plugins")
async def list_plugins(query: str = "", category: str = "all", user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        query_filter = f"AND (p.name LIKE '%{query}%' OR p.description LIKE '%{query}%')" if query else ""
        cat_filter = f"AND p.category = '{category}'" if category != "all" else ""
        rows = conn.execute(
            f"SELECT p.id, p.name, p.description, p.category, p.price, p.install_count, p.rating, p.publisher, p.created_at "
            f"FROM plugins p "
            f"LEFT JOIN plugin_installs pi ON pi.plugin_id = p.id AND pi.user_id = ? "
            f"WHERE p.enabled = 1 {query_filter} {cat_filter} "
            f"ORDER BY p.install_count DESC, p.rating DESC LIMIT 100",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("/plugins/{plugin_id}/install")
async def install_plugin(plugin_id: str, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        row = conn.execute("SELECT id, name, price FROM plugins WHERE id = ? AND enabled = 1", (plugin_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plugin not found")
        conn.execute(
            "INSERT OR REPLACE INTO plugin_installs (plugin_id, user_id, installed_at) VALUES (?, ?, ?)",
            (plugin_id, user_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.execute("UPDATE plugins SET install_count = install_count + 1 WHERE id = ?", (plugin_id,))
        conn.commit()
    return {"plugin_id": plugin_id, "name": row["name"], "installed": True}


@router.post("/plugins/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, req: dict, user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        install = conn.execute(
            "SELECT plugin_id FROM plugin_installs WHERE plugin_id = ? AND user_id = ?",
            (plugin_id, user_id),
        ).fetchone()
        if not install:
            raise HTTPException(status_code=403, detail="Plugin not installed")
        plugin = conn.execute("SELECT name, config FROM plugins WHERE id = ?", (plugin_id,)).fetchone()
        if not plugin:
            raise HTTPException(status_code=404, detail="Plugin not found")
        config = json.loads(plugin["config"] or "{}")
    result = {
        "plugin": plugin["name"],
        "input": req.get("args", {}),
        "config_used": list(config.keys()),
        "output": f"Plugin {plugin['name']} executed successfully with args {json.dumps(req.get('args', {}))[:200]}",
    }
    return result


@router.get("/plugins/categories")
async def get_plugin_categories(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category, COUNT(*) as count FROM plugins WHERE enabled = 1 GROUP BY category ORDER BY count DESC"
        ).fetchall()
        return {"categories": [dict(r) for r in rows]}


@router.post("/plugins/submit")
async def submit_plugin(req: dict, user_id: str = Depends(require_verified_email)):
    plugin_id = str(uuid.uuid4())
    name = req.get("name", "")
    description = req.get("description", "")
    category = req.get("category", "other")
    price = req.get("price", 0)
    config = json.dumps(req.get("config", {}))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO plugins (id, user_id, name, description, category, price, config, enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (plugin_id, user_id, name, description, category, price, config, 0, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return {"plugin_id": plugin_id, "name": name, "status": "pending_review"}


@router.get("/plugins/featured")
async def get_featured_plugins(user_id: str = Depends(require_verified_email)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, description, category, price, install_count, rating, publisher FROM plugins WHERE enabled = 1 AND install_count > 100 ORDER BY rating DESC, install_count DESC LIMIT 10"
        ).fetchall()
        return {"featured": [dict(r) for r in rows]}
