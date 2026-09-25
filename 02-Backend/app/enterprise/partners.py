"""Partner/ecosystem APIs."""

import uuid
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PartnerAccount:
    id: str
    tenant_id: str
    name: str
    api_key: str
    scopes: List[str] = field(default_factory=list)
    is_active: bool = True
    rate_limit: int = 1000
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp)


class PartnerService:
    def __init__(self):
        self._accounts: Dict[str, PartnerAccount] = {}
        self._api_key_index: Dict[str, PartnerAccount] = {}

    def create_partner(self, tenant_id: str, name: str, scopes: List[str] = None) -> PartnerAccount:
        partner_id = str(uuid.uuid4())
        api_key = f"pk_{uuid.uuid4().hex}"
        account = PartnerAccount(
            id=partner_id,
            tenant_id=tenant_id,
            name=name,
            api_key=api_key,
            scopes=scopes or ["read"],
        )
        self._accounts[partner_id] = account
        self._api_key_index[api_key] = account
        logger.info("Created partner account %s for tenant %s", partner_id, tenant_id)
        return account

    def get_partner(self, partner_id: str) -> Optional[PartnerAccount]:
        return self._accounts.get(partner_id)

    def get_by_api_key(self, api_key: str) -> Optional[PartnerAccount]:
        return self._api_key_index.get(api_key)

    def list_partners(self, tenant_id: str = None) -> List[PartnerAccount]:
        accounts = list(self._accounts.values())
        if tenant_id:
            accounts = [a for a in accounts if a.tenant_id == tenant_id]
        return accounts

    def revoke_api_key(self, partner_id: str) -> bool:
        account = self._accounts.get(partner_id)
        if not account:
            return False
        if account.api_key in self._api_key_index:
            del self._api_key_index[account.api_key]
        account.is_active = False
        return True

    def update_scopes(self, partner_id: str, scopes: List[str]) -> Optional[PartnerAccount]:
        account = self._accounts.get(partner_id)
        if not account:
            return None
        account.scopes = scopes
        return account

    def check_rate_limit(self, partner_id: str) -> bool:
        account = self._accounts.get(partner_id)
        if not account:
            return False
        return account.rate_limit > 0


partner_service = PartnerService()
