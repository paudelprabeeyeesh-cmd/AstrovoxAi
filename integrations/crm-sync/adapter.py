"""CRM sync integration."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Contact:
    id: str
    name: str
    email: str
    company: str
    phone: Optional[str] = None


class CRMSync:
    def __init__(self, provider: str = "salesforce"):
        self.provider = provider

    def sync_contacts(self, org_id: str) -> list[Contact]:
        return [
            Contact(id="crm-1", name="Alice Smith", email="alice@example.com", company="Acme", phone="555-0101"),
            Contact(id="crm-2", name="Bob Jones", email="bob@example.com", company="Acme", phone="555-0102"),
        ]

    def log_interaction(self, contact_id: str, interaction_type: str, notes: str) -> dict:
        return {
            "contact_id": contact_id,
            "interaction_type": interaction_type,
            "notes": notes,
            "synced": True,
        }


crm_sync = CRMSync()
