"""Authorization with ownership, scope, and resource-level checks."""
import logging
from typing import Optional, Set

logger = logging.getLogger(__name__)


class AuthorizationManager:
    def __init__(self):
        self._user_scopes: dict[str, Set[str]] = {}
        self._resource_owners: dict[str, str] = {}

    def grant_scopes(self, user_id: str, scopes: Set[str]):
        self._user_scopes[user_id] = self._user_scopes.get(user_id, set()) | scopes

    def revoke_scope(self, user_id: str, scope: str):
        if user_id in self._user_scopes:
            self._user_scopes[user_id].discard(scope)

    def has_scope(self, user_id: str, scope: str) -> bool:
        return scope in self._user_scopes.get(user_id, set())

    def set_owner(self, resource_id: str, owner_id: str):
        self._resource_owners[resource_id] = owner_id

    def check_access(self, user_id: str, resource_id: str, required_scope: Optional[str] = None) -> bool:
        owner = self._resource_owners.get(resource_id)
        if owner is None:
            return True
        if user_id == owner:
            return True
        if required_scope and self.has_scope(user_id, required_scope):
            return True
        logger.warning("Access denied: user=%s resource=%s scope=%s", user_id, resource_id, required_scope)
        return False

    def is_owner(self, user_id: str, resource_id: str) -> bool:
        return self._resource_owners.get(resource_id) == user_id


auth_manager = AuthorizationManager()
