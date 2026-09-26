"""Ecosystem package initialization."""
from .plugin_registry import PluginRegistry, PluginManifest
from .webhook_manager import WebhookManager, Webhook, WebhookDelivery
from .integration_adapter import IntegrationAdapter, IntegrationConfig

__all__ = [
    "PluginRegistry",
    "PluginManifest",
    "WebhookManager",
    "Webhook",
    "WebhookDelivery",
    "IntegrationAdapter",
    "IntegrationConfig",
]
