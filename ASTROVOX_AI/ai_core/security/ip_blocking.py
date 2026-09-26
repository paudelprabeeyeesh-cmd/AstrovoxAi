from typing import Optional, Set, Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging
import ipaddress

logger = logging.getLogger(__name__)


@dataclass
class IPBlockEntry:
    ip: str
    reason: str
    blocked_at: float
    expires_at: Optional[float] = None
    is_permanent: bool = False


class IPBlocker:
    def __init__(self):
        self._blocked_ips: Dict[str, IPBlockEntry] = {}
        self._blocked_ranges: List[ipaddress.IPv4Network] = []
        self._permanent_blocks: Set[str] = set()

    def block_ip(self, ip: str, reason: str = "Manual block", ttl_hours: Optional[int] = None, permanent: bool = False) -> bool:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            logger.warning("Attempted to block invalid IP: %s", ip)
            return False
        now = datetime.utcnow().timestamp()
        expires_at = None
        if not permanent and ttl_hours is not None:
            expires_at = now + ttl_hours * 3600
        entry = IPBlockEntry(
            ip=ip,
            reason=reason,
            blocked_at=now,
            expires_at=expires_at,
            is_permanent=permanent,
        )
        self._blocked_ips[ip] = entry
        if permanent:
            self._permanent_blocks.add(ip)
        logger.info("Blocked IP %s: %s", ip, reason)
        return True

    def unblock_ip(self, ip: str) -> bool:
        if ip in self._blocked_ips:
            del self._blocked_ips[ip]
            self._permanent_blocks.discard(ip)
            logger.info("Unblocked IP %s", ip)
            return True
        return False

    def block_range(self, cidr: str, reason: str = "Range block") -> bool:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            self._blocked_ranges.append(network)
            logger.info("Blocked IP range %s: %s", cidr, reason)
            return True
        except ValueError:
            logger.warning("Attempted to block invalid CIDR: %s", cidr)
            return False

    def is_blocked(self, ip: str) -> tuple[bool, Optional[str]]:
        if ip in self._permanent_blocks:
            return True, "Permanent IP block"
        if ip in self._blocked_ips:
            entry = self._blocked_ips[ip]
            if entry.expires_at and datetime.utcnow().timestamp() > entry.expires_at:
                del self._blocked_ips[ip]
                self._permanent_blocks.discard(ip)
                return False, None
            return True, entry.reason
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self._blocked_ranges:
                if ip_obj in network:
                    return True, f"IP in blocked range {network}"
        except ValueError:
            logger.debug("IP %s is not in any blocked range", ip)
        return False, None

    def cleanup_expired(self) -> int:
        now = datetime.utcnow().timestamp()
        expired = [ip for ip, entry in self._blocked_ips.items()
                   if not entry.is_permanent and entry.expires_at and now > entry.expires_at]
        for ip in expired:
            del self._blocked_ips[ip]
        return len(expired)

    def get_blocked_ips(self, include_permanent: bool = True, include_temporary: bool = True) -> List[Dict[str, Any]]:
        result = []
        for ip, entry in self._blocked_ips.items():
            if entry.is_permanent and not include_permanent:
                continue
            if not entry.is_permanent and not include_temporary:
                continue
            result.append({
                'ip': entry.ip,
                'reason': entry.reason,
                'blocked_at': datetime.fromtimestamp(entry.blocked_at).isoformat(),
                'expires_at': datetime.fromtimestamp(entry.expires_at).isoformat() if entry.expires_at else None,
                'is_permanent': entry.is_permanent,
            })
        return result
