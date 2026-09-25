import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CRMProvider(Enum):
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    PIPEDRIVE = "pipedrive"
    ZOHO = "zoho"


@dataclass
class CRMContact:
    contact_id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CRMDeal:
    deal_id: str
    title: str
    amount: float
    stage: str
    contact_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    synced_count: int
    failed_count: int
    errors: List[str] = field(default_factory=list)


class CRMSyncAdapter:
    def __init__(self, api_client):
        self.api_client = api_client
        self._contacts: Dict[str, CRMContact] = {}
        self._deals: Dict[str, CRMDeal] = {}

    def register_contact(self, contact: CRMContact):
        self._contacts[contact.contact_id] = contact
        logger.info(f"Registered CRM contact {contact.contact_id}")

    def register_deal(self, deal: CRMDeal):
        self._deals[deal.deal_id] = deal
        logger.info(f"Registered CRM deal {deal.deal_id}")

    def sync_conversation_to_crm(self, conversation_id: str, provider: CRMProvider = CRMProvider.SALESFORCE) -> SyncResult:
        try:
            conversation = self.api_client.get_conversation(conversation_id)
            contact = CRMContact(
                contact_id=f"contact-{conversation_id}",
                name=conversation.title,
                email=f"conv-{conversation_id}@astrovox.ai",
                metadata={"conversation_id": conversation_id}
            )
            self._contacts[contact.contact_id] = contact
            deal = CRMDeal(
                deal_id=f"deal-{conversation_id}",
                title=f"Astrovox: {conversation.title}",
                amount=0.0,
                stage="qualification",
                contact_id=contact.contact_id,
                metadata={"conversation_id": conversation_id, "message_count": len(conversation.messages)}
            )
            self._deals[deal.deal_id] = deal
            logger.info(f"Synced conversation {conversation_id} to CRM as contact {contact.contact_id} and deal {deal.deal_id}")
            return SyncResult(synced_count=2, failed_count=0)
        except Exception as e:
            logger.error(f"Failed to sync conversation {conversation_id} to CRM: {e}")
            return SyncResult(synced_count=0, failed_count=1, errors=[str(e)])

    def sync_from_crm(self, contact_id: str) -> SyncResult:
        contact = self._contacts.get(contact_id)
        if not contact:
            return SyncResult(synced_count=0, failed_count=1, errors=[f"Contact {contact_id} not found"])
        try:
            conv = self.api_client.create_conversation(title=f"CRM: {contact.name}")
            logger.info(f"Synced CRM contact {contact_id} to conversation {conv.id}")
            return SyncResult(synced_count=1, failed_count=0)
        except Exception as e:
            logger.error(f"Failed to sync CRM contact {contact_id}: {e}")
            return SyncResult(synced_count=0, failed_count=1, errors=[str(e)])

    def bulk_sync(self, conversation_ids: List[str]) -> Dict[str, SyncResult]:
        results = {}
        for cid in conversation_ids:
            results[cid] = self.sync_conversation_to_crm(cid)
        return results

    def get_contact(self, contact_id: str) -> Optional[CRMContact]:
        return self._contacts.get(contact_id)

    def get_deal(self, deal_id: str) -> Optional[CRMDeal]:
        return self._deals.get(deal_id)

    def list_contacts(self) -> List[CRMContact]:
        return list(self._contacts.values())

    def list_deals(self) -> List[CRMDeal]:
        return list(self._deals.values())

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        contact = self._contacts.get(contact_id)
        if not contact:
            return False
        for key, value in updates.items():
            if hasattr(contact, key):
                setattr(contact, key, value)
        logger.info(f"Updated CRM contact {contact_id}")
        return True

    def delete_contact(self, contact_id: str) -> bool:
        if contact_id in self._contacts:
            del self._contacts[contact_id]
            logger.info(f"Deleted CRM contact {contact_id}")
            return True
        return False

    def delete_deal(self, deal_id: str) -> bool:
        if deal_id in self._deals:
            del self._deals[deal_id]
            logger.info(f"Deleted CRM deal {deal_id}")
            return True
        return False
