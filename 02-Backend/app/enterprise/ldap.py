"""LDAP authentication integration."""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LDAPConfig:
    server: str
    bind_dn: str
    base_dn: str
    use_ssl: bool = True
    user_search_filter: str = "(uid={username})"
    group_search_filter: str = "(memberUid={username})"


class LDAPClient:
    def __init__(self, config: LDAPConfig):
        self.config = config

    def authenticate(self, username: str, password: str) -> dict:
        try:
            import ldap3
        except ImportError:
            logger.error("ldap3 is not installed. Install it to enable LDAP.")
            raise RuntimeError("LDAP library not installed")
        server = ldap3.Server(self.config.server, use_ssl=self.config.use_ssl)
        conn = ldap3.Connection(server, user=self.config.bind_dn, password=password, auto_bind=True)
        user_search_base = self.config.base_dn
        search_filter = self.config.user_search_filter.format(username=username)
        conn.search(user_search_base, search_filter, attributes=["cn", "mail", "memberOf"])
        if not conn.entries:
            raise ValueError("User not found in LDAP")
        entry = conn.entries[0]
        groups = []
        if "memberOf" in entry:
            groups = [g.split(",")[0].split("=")[-1] for g in entry.memberOf.values]
        return {
            "username": username,
            "cn": entry.cn.value,
            "mail": entry.mail.value if "mail" in entry else None,
            "groups": groups,
            "authenticated": True,
        }

    def sync_groups(self, org_id: str) -> list[str]:
        return [f"org-{org_id}-admin", f"org-{org_id}-member"]


ldap_client = LDAPClient(LDAPConfig(server="ldap://localhost", bind_dn="cn=admin,dc=example,dc=com", base_dn="dc=example,dc=com"))
