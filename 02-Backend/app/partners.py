import uuid
import secrets
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class PartnerAccount:
    id: str
    tenant_id: str
    name: str
    api_key: str
    scopes: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class PartnerService:
    def __init__(self):
        self.accounts: Dict[str, PartnerAccount] = {}

    def create_partner(self, tenant_id: str, name: str, scopes: List[str] = None) -> PartnerAccount:
        account_id = str(uuid.uuid4())
        api_key = f"pk_{secrets.token_urlsafe(32)}"
        account = PartnerAccount(
            id=account_id,
            tenant_id=tenant_id,
            name=name,
            api_key=api_key,
            scopes=scopes or ["read"],
        )
        self.accounts[account_id] = account
        self._persist(account)
        return account

    def _persist(self, account: PartnerAccount) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO partner_accounts (id, tenant_id, name, api_key, scopes, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (account.id, account.tenant_id, account.name, account.api_key, json.dumps(account.scopes), 1 if account.is_active else 0),
            )
            conn.commit()

    def get_account_by_api_key(self, api_key: str) -> Optional[PartnerAccount]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM partner_accounts WHERE api_key = ? AND is_active = 1", (api_key,)).fetchone()
            if row:
                data = dict(row)
                data["scopes"] = json.loads(data["scopes"] or "[]")
                return PartnerAccount(**data)
            return None

    def list_partners(self, tenant_id: str = None) -> List[PartnerAccount]:
        accounts = list(self.accounts.values())
        if tenant_id:
            accounts = [a for a in accounts if a.tenant_id == tenant_id]
        return accounts

    def deactivate_partner(self, account_id: str) -> bool:
        account = self.accounts.get(account_id)
        if not account:
            return False
        account.is_active = False
        with get_db() as conn:
            conn.execute("UPDATE partner_accounts SET is_active = 0 WHERE id = ?", (account_id,))
            conn.commit()
        return True


partner_service = PartnerService()
