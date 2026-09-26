import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_verified_email
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["integrations"])


@router.post("/integrations/chrome/browse")
async def chrome_browse(url: str, task: str = "", user_id: str = Depends(require_verified_email)):
    try:
        task_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO integration_tasks (id, user_id, integration, action, target, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, user_id, "chrome", "browse", url, "running", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": task_id, "integration": "chrome", "action": "browse", "url": url, "task": task}
    except Exception as e:
        logger.error(f"Chrome integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/excel/edit")
async def excel_edit(file_id: str, operation: str, user_id: str = Depends(require_verified_email)):
    try:
        task_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO integration_tasks (id, user_id, integration, action, target, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, user_id, "excel", operation, file_id, "running", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": task_id, "integration": "excel", "action": operation, "file_id": file_id}
    except Exception as e:
        logger.error(f"Excel integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/powerpoint/edit")
async def powerpoint_edit(file_id: str, operation: str, user_id: str = Depends(require_verified_email)):
    try:
        task_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO integration_tasks (id, user_id, integration, action, target, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, user_id, "powerpoint", operation, file_id, "running", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": task_id, "integration": "powerpoint", "action": operation, "file_id": file_id}
    except Exception as e:
        logger.error(f"PowerPoint integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/slack/tag")
async def slack_tag(channel: str, message: str, user_id: str = Depends(require_verified_email)):
    try:
        task_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO integration_tasks (id, user_id, integration, action, target, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, user_id, "slack", "tag", channel, "running", datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        return {"id": task_id, "integration": "slack", "action": "tag", "channel": channel, "message": message[:200]}
    except Exception as e:
        logger.error(f"Slack integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
