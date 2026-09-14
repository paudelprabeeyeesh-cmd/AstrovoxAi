import uuid
from datetime import datetime

from app.core.encryption import decrypt, encrypt
from app.database import get_db


def create_integration(user_id: str, type_: str, config: str) -> dict:
    integration_id = str(uuid.uuid4())
    encrypted_config = encrypt(config)
    with get_db() as conn:
        conn.execute(
            'INSERT INTO integrations (id, user_id, type, config, created_at) VALUES (?, ?, ?, ?, ?)',
            (
                integration_id,
                user_id,
                type_,
                encrypted_config,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
    return {'id': integration_id, 'type': type_}


def list_integrations(user_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, type, config, created_at FROM integrations WHERE user_id = ?',
            (user_id,),
        ).fetchall()
        return [
            {
                'id': r['id'],
                'type': r['type'],
                'config': decrypt(r['config']),
                'created_at': r['created_at'],
            }
            for r in rows
        ]


def delete_integration(integration_id: str, user_id: str):
    with get_db() as conn:
        conn.execute(
            'DELETE FROM integrations WHERE id = ? AND user_id = ?',
            (integration_id, user_id),
        )
        conn.commit()
