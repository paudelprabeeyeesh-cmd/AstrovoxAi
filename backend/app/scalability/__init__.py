"""Scalability and global infrastructure package initialization."""
from .auto_scaler import AutoScaler, ScalingPolicy
from .load_balancer import LoadBalancer, BalancerConfig
from .cdn_manager import CDNManager, CDNConfig
from .dns_manager import DNSManager, DNSRecord

__all__ = [
    "AutoScaler",
    "ScalingPolicy",
    "LoadBalancer",
    "BalancerConfig",
    "CDNManager",
    "CDNConfig",
    "DNSManager",
    "DNSRecord",
]
