
import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from .database import get_db
from .audit import log_action


def create_white_label_config(org_id: str, brand_name: Optional[str] = None, **kwargs) -> dict:
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM white_label_configs WHERE org_id = ?", (org_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE white_label_configs SET brand_name = ?, logo_url = ?, favicon_url = ?, primary_color = ?, secondary_color = ?, accent_color = ?, custom_css = ?, email_from_name = ?, email_from_address = ?, support_email = ?, privacy_policy_url = ?, terms_of_service_url = ?, hide_powered_by = ?, updated_at = ? WHERE org_id = ?",
                (
                    brand_name, kwargs.get("logo_url"), kwargs.get("favicon_url"), kwargs.get("primary_color", "#1a1a2e"),
                    kwargs.get("secondary_color", "#16213e"), kwargs.get("accent_color", "#e94560"), kwargs.get("custom_css"),
                    kwargs.get("email_from_name"), kwargs.get("email_from_address"), kwargs.get("support_email"),
                    kwargs.get("privacy_policy_url"), kwargs.get("terms_of_service_url"), 1 if kwargs.get("hide_powered_by") else 0, now, org_id,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO white_label_configs (id, org_id, brand_name, logo_url, favicon_url, primary_color, secondary_color, accent_color, custom_css, email_from_name, email_from_address, support_email, privacy_policy_url, terms_of_service_url, hide_powered_by, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    config_id, org_id, brand_name, kwargs.get("logo_url"), kwargs.get("favicon_url"), kwargs.get("primary_color", "#1a1a2e"),
                    kwargs.get("secondary_color", "#16213e"), kwargs.get("accent_color", "#e94560"), kwargs.get("custom_css"),
                    kwargs.get("email_from_name"), kwargs.get("email_from_address"), kwargs.get("support_email"),
                    kwargs.get("privacy_policy_url"), kwargs.get("terms_of_service_url"), 1 if kwargs.get("hide_powered_by") else 0,
                    json.dumps(kwargs.get("metadata", {})), now, now,
                ),
            )
        conn.execute("UPDATE organizations SET white_label_enabled = 1, updated_at = ? WHERE id = ?", (now, org_id))
        conn.commit()
    log_action(None, "create_white_label", f"org:{org_id}", {"brand_name": brand_name})
    return get_white_label_config(org_id)


def get_white_label_config(org_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM white_label_configs WHERE org_id = ?", (org_id,)).fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("metadata"):
            try:
                data["metadata"] = json.loads(data["metadata"])
            except Exception:
                pass
        return data


def update_white_label_config(org_id: str, **kwargs) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT id FROM white_label_configs WHERE org_id = ?", (org_id,)).fetchone()
        if not row:
            return create_white_label_config(org_id, **kwargs)
        now = datetime.now(timezone.utc).isoformat()
        updates = {}
        for key in ["brand_name", "logo_url", "favicon_url", "primary_color", "secondary_color", "accent_color", "custom_css", "email_from_name", "email_from_address", "support_email", "privacy_policy_url", "terms_of_service_url"]:
            if key in kwargs:
                updates[key] = kwargs[key]
        if "hide_powered_by" in kwargs:
            updates["hide_powered_by"] = 1 if kwargs["hide_powered_by"] else 0
        if "metadata" in kwargs:
            updates["metadata"] = json.dumps(kwargs["metadata"])
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [org_id]
        conn.execute(f"UPDATE white_label_configs SET {set_clause} WHERE org_id = ?", values)
        conn.commit()
    return get_white_label_config(org_id)


def delete_white_label_config(org_id: str, requester_id: str) -> bool:
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("UPDATE organizations SET white_label_enabled = 0, updated_at = ? WHERE id = ?", (now, org_id))
        cur = conn.execute("DELETE FROM white_label_configs WHERE org_id = ?", (org_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        log_action(requester_id, "delete_white_label", f"org:{org_id}", {})
    return deleted
