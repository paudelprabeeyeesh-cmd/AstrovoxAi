"""Resource-level access control lists."""

from typing import Dict, Optional, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ACLAction(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"


class ACLSubjectType(Enum):
    USER = "user"
    GROUP = "group"
    SERVICE = "service"
    API_KEY = "api_key"


@dataclass
class ACLEntry:
    subject_id: str
    subject_type: ACLSubjectType
    actions: Set[ACLAction]
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceACL:
    resource_type: str
    resource_id: str
    owner_id: str
    entries: List[ACLEntry] = field(default_factory=list)
    is_public: bool = False


class ACLManager:
    _acls: Dict[str, ResourceACL] = {}

    @classmethod
    def _key(cls, resource_type: str, resource_id: str) -> str:
        return f"{resource_type}:{resource_id}"

    @classmethod
    def create_resource(cls, resource_type: str, resource_id: str, owner_id: str) -> ResourceACL:
        acl = ResourceACL(resource_type=resource_type, resource_id=resource_id, owner_id=owner_id)
        cls._acls[cls._key(resource_type, resource_id)] = acl
        return acl

    @classmethod
    def grant(cls, resource_type: str, resource_id: str, subject_id: str, subject_type: ACLSubjectType, actions: Set[ACLAction]) -> None:
        acl = cls._acls.get(cls._key(resource_type, resource_id))
        if not acl:
            return
        entry = ACLEntry(subject_id=subject_id, subject_type=subject_type, actions=actions)
        acl.entries.append(entry)

    @classmethod
    def revoke(cls, resource_type: str, resource_id: str, subject_id: str, action: Optional[ACLAction] = None) -> None:
        acl = cls._acls.get(cls._key(resource_type, resource_id))
        if not acl:
            return
        acl.entries = [
            e for e in acl.entries
            if not (e.subject_id == subject_id and (action is None or action in e.actions))
        ]

    @classmethod
    def check_permission(cls, resource_type: str, resource_id: str, subject_id: str, action: ACLAction, subject_type: ACLSubjectType = ACLSubjectType.USER) -> bool:
        acl = cls._acls.get(cls._key(resource_type, resource_id))
        if not acl:
            return False
        if acl.is_public and action == ACLAction.READ:
            return True
        if acl.owner_id == subject_id:
            return True
        for entry in acl.entries:
            if entry.subject_id == subject_id and entry.subject_type == subject_type:
                if entry.expires_at and entry.expires_at < datetime.now(timezone.utc):
                    continue
                if action in entry.actions or ACLAction.ADMIN in entry.actions:
                    return True
        return False
