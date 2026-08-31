"""Enterprise Administration — organizations, teams, user management."""

import time
import secrets
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class OrganizationRole(Enum):
    """Roles within an organization."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(Enum):
    """Team invitation status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


@dataclass
class Organization:
    """An organization/workspace."""
    id: str
    name: str
    slug: str
    owner_id: str
    created_at: float
    plan: str = "free"
    settings: dict = field(default_factory=dict)
    is_active: bool = True


@dataclass
class OrganizationMember:
    """A member of an organization."""
    org_id: str
    user_id: str
    role: OrganizationRole
    joined_at: float
    is_active: bool = True


@dataclass
class TeamInvitation:
    """A team invitation."""
    id: str
    org_id: str
    email: str
    role: OrganizationRole
    invited_by: str
    status: InvitationStatus
    created_at: float
    expires_at: float


@dataclass
class AuditLogEntry:
    """An audit log entry."""
    id: str
    org_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: float
    details: dict = field(default_factory=dict)
    ip_address: str = ""


class OrganizationManager:
    """Manage organizations and teams."""

    def __init__(self):
        self._organizations: dict[str, Organization] = {}
        self._members: dict[str, list[OrganizationMember]] = {}
        self._user_orgs: dict[str, list[str]] = {}
        self._invitations: dict[str, TeamInvitation] = {}
        self._audit_log: list[AuditLogEntry] = []

    def create_organization(
        self,
        name: str,
        owner_id: str,
        slug: str = "",
    ) -> Organization:
        """Create a new organization."""
        org_id = secrets.token_hex(8)
        if not slug:
            slug = name.lower().replace(" ", "-") + "-" + org_id[:4]

        org = Organization(
            id=org_id,
            name=name,
            slug=slug,
            owner_id=owner_id,
            created_at=time.time(),
        )

        self._organizations[org_id] = org

        member = OrganizationMember(
            org_id=org_id,
            user_id=owner_id,
            role=OrganizationRole.OWNER,
            joined_at=time.time(),
        )
        self._members[org_id] = [member]
        self._user_orgs.setdefault(owner_id, []).append(org_id)

        self._log_action(org_id, owner_id, "org.created", "organization", org_id)

        return org

    def get_organization(self, org_id: str) -> Optional[Organization]:
        return self._organizations.get(org_id)

    def get_user_organizations(self, user_id: str) -> list[Organization]:
        org_ids = self._user_orgs.get(user_id, [])
        return [self._organizations[oid] for oid in org_ids if oid in self._organizations]

    def invite_member(
        self,
        org_id: str,
        email: str,
        role: OrganizationRole,
        invited_by: str,
    ) -> Optional[TeamInvitation]:
        """Invite a member to the organization."""
        if org_id not in self._organizations:
            return None

        invitation = TeamInvitation(
            id=secrets.token_hex(8),
            org_id=org_id,
            email=email,
            role=role,
            invited_by=invited_by,
            status=InvitationStatus.PENDING,
            created_at=time.time(),
            expires_at=time.time() + 604800,
        )

        self._invitations[invitation.id] = invitation
        self._log_action(org_id, invited_by, "member.invited", "invitation", invitation.id)

        return invitation

    def accept_invitation(self, invitation_id: str, user_id: str) -> bool:
        """Accept a team invitation."""
        invitation = self._invitations.get(invitation_id)
        if not invitation or invitation.status != InvitationStatus.PENDING:
            return False

        if time.time() > invitation.expires_at:
            invitation.status = InvitationStatus.EXPIRED
            return False

        invitation.status = InvitationStatus.ACCEPTED

        member = OrganizationMember(
            org_id=invitation.org_id,
            user_id=user_id,
            role=invitation.role,
            joined_at=time.time(),
        )
        self._members.setdefault(invitation.org_id, []).append(member)
        self._user_orgs.setdefault(user_id, []).append(invitation.org_id)

        self._log_action(
            invitation.org_id, user_id, "member.joined", "organization", invitation.org_id
        )

        return True

    def remove_member(self, org_id: str, user_id: str, removed_by: str) -> bool:
        """Remove a member from the organization."""
        members = self._members.get(org_id, [])
        for member in members:
            if member.user_id == user_id:
                member.is_active = False
                self._log_action(org_id, removed_by, "member.removed", "user", user_id)
                return True
        return False

    def update_member_role(
        self, org_id: str, user_id: str, new_role: OrganizationRole, updated_by: str
    ) -> bool:
        """Update a member's role."""
        members = self._members.get(org_id, [])
        for member in members:
            if member.user_id == user_id:
                member.role = new_role
                self._log_action(
                    org_id, updated_by, "member.role_updated", "user", user_id,
                    details={"new_role": new_role.value},
                )
                return True
        return False

    def get_members(self, org_id: str) -> list[OrganizationMember]:
        return [m for m in self._members.get(org_id, []) if m.is_active]

    def get_invitations(self, org_id: str) -> list[TeamInvitation]:
        return [i for i in self._invitations.values() if i.org_id == org_id]

    def _log_action(
        self,
        org_id: str,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict = None,
    ):
        """Log an audit action."""
        entry = AuditLogEntry(
            id=secrets.token_hex(8),
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=time.time(),
            details=details or {},
        )
        self._audit_log.append(entry)

    def get_audit_log(
        self,
        org_id: str,
        limit: int = 100,
        since: float = 0,
    ) -> list[AuditLogEntry]:
        """Get audit log for an organization."""
        entries = [
            e for e in self._audit_log
            if e.org_id == org_id and e.timestamp >= since
        ]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_org_stats(self, org_id: str) -> dict:
        """Get organization statistics."""
        members = self.get_members(org_id)
        invitations = self.get_invitations(org_id)

        return {
            "total_members": len(members),
            "active_members": len([m for m in members if m.is_active]),
            "pending_invitations": len([
                i for i in invitations if i.status == InvitationStatus.PENDING
            ]),
            "roles": {
                role.value: len([m for m in members if m.role == role])
                for role in OrganizationRole
            },
        }


org_manager = OrganizationManager()
