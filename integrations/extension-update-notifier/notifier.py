import json
import time
import logging
import requests
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Thread, Lock

logger = logging.getLogger(__name__)


@dataclass
class ExtensionVersion:
    name: str
    version: str
    url: str
    checksum: str
    published_at: str
    changelog: str
    min_platform_version: str = "2.0.0"


@dataclass
class UpdateNotification:
    name: str
    current_version: str
    latest_version: str
    changelog: str
    url: str
    severity: str
    released_at: str


class ExtensionUpdateNotifier:
    def __init__(self, registry_url: str = "https://extensions.astrovox.ai", check_interval: int = 3600):
        self.registry_url = registry_url.rstrip('/')
        self.check_interval = check_interval
        self.installed: Dict[str, str] = {}
        self.available: Dict[str, ExtensionVersion] = {}
        self._callbacks: List[Callable[[UpdateNotification], None]] = []
        self._running = False
        self._lock = Lock()
        self._thread: Optional[Thread] = None

    def register_extension(self, name: str, version: str):
        with self._lock:
            self.installed[name] = version
        logger.info(f"Registered extension {name} v{version}")

    def on_update(self, callback: Callable[[UpdateNotification], None]):
        self._callbacks.append(callback)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Extension update notifier started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Extension update notifier stopped")

    def _poll_loop(self):
        while self._running:
            try:
                self.check_for_updates()
            except Exception as e:
                logger.error(f"Update check failed: {e}")
            time.sleep(self.check_interval)

    def check_for_updates(self) -> List[UpdateNotification]:
        notifications: List[UpdateNotification] = []
        with self._lock:
            extensions = list(self.installed.items())
        for name, current_version in extensions:
            try:
                latest = self._fetch_latest(name)
                if latest and latest.version != current_version:
                    severity = self._determine_severity(current_version, latest.version)
                    changelog = latest.changelog or "No changelog available."
                    notification = UpdateNotification(
                        name=name,
                        current_version=current_version,
                        latest_version=latest.version,
                        changelog=changelog,
                        url=latest.url,
                        severity=severity,
                        released_at=latest.published_at
                    )
                    notifications.append(notification)
                    self._notify(notification)
            except Exception as e:
                logger.error(f"Failed to check updates for {name}: {e}")
        return notifications

    def _fetch_latest(self, name: str) -> Optional[ExtensionVersion]:
        url = f"{self.registry_url}/extensions/{name}/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return ExtensionVersion(
            name=data["name"],
            version=data["version"],
            url=data["url"],
            checksum=data.get("checksum", ""),
            published_at=data.get("published_at", ""),
            changelog=data.get("changelog", ""),
            min_platform_version=data.get("min_platform_version", "2.0.0")
        )

    def _determine_severity(self, current: str, latest: str) -> str:
        try:
            current_parts = [int(p.split('-')[0]) for p in current.split('.')[:3]]
            latest_parts = [int(p.split('-')[0]) for p in latest.split('.')[:3]]
            if latest_parts[0] > current_parts[0]:
                return "major"
            elif latest_parts[1] > current_parts[1]:
                return "minor"
            else:
                return "patch"
        except Exception:
            return "unknown"

    def _notify(self, notification: UpdateNotification):
        for callback in self._callbacks:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

    def get_available_updates(self) -> List[UpdateNotification]:
        return self.check_for_updates()

    def get_update_manifest(self, name: str) -> Optional[Dict[str, Any]]:
        url = f"{self.registry_url}/extensions/{name}/manifest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
