"""IP allowlist and denylist enforcement.

Blocks requests from denylisted IPs and restricts access to
allowlisted IPs when configured. Supports CIDR ranges.
"""

from __future__ import annotations

import ipaddress
import logging
import threading
from typing import List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class IPFilter:
    """IP allowlist / denylist enforcement."""

    def __init__(
        self,
        allowlist: Optional[List[str]] = None,
        denylist: Optional[List[str]] = None,
    ) -> None:
        self._allowlist: Optional[List[ipaddress.IPv4Network | ipaddress.IPv6Network]] = None
        self._denylist: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        self._lock = threading.Lock()

        if allowlist:
            self._allowlist = [ipaddress.ip_network(cidr, strict=False) for cidr in allowlist]
        if denylist:
            self._denylist = [ipaddress.ip_network(cidr, strict=False) for cidr in denylist]

    def _parse(self, ip_str: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            return ipaddress.ip_address(ip_str)
        except ValueError:
            return None

    def check(self, ip_str: str) -> Tuple[bool, Optional[str]]:
        addr = self._parse(ip_str)
        if addr is None:
            return False, "invalid_ip"

        for network in self._denylist:
            if addr in network:
                return False, "denylisted"

        if self._allowlist is not None:
            allowed = any(addr in network for network in self._allowlist)
            if not allowed:
                return False, "not_allowlisted"

        return True, None

    def add_denylist(self, cidr: str) -> None:
        with self._lock:
            self._denylist.append(ipaddress.ip_network(cidr, strict=False))

    def remove_denylist(self, cidr: str) -> None:
        with self._lock:
            self._denylist = [n for n in self._denylist if str(n) != cidr]


ip_filter = IPFilter()
