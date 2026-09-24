import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SecretBackend(Enum):
    KUBERNETES = "kubernetes"
    HASHICORP_VAULT = "vault"
    ENVIRONMENT = "environment"


class RotationStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    NOT_FOUND = "not_found"
    ALREADY_ROTATED = "already_rotated"


@dataclass
class RotationRecord:
    secret_name: str
    previous_version: Optional[str]
    current_version: str
    rotated_at: str
    backend: SecretBackend


class SecretRotationService:
    def __init__(self, backend: SecretBackend = SecretBackend.ENVIRONMENT) -> None:
        self.backend = backend
        self._rotation_history: dict[str, RotationRecord] = {}
        self._schedule: dict[str, datetime] = {}

    def rotate_secret(self, secret_name: str) -> str:
        logger.info("Rotating secret: %s", secret_name)

        if self.backend == SecretBackend.KUBERNETES:
            new_value = self._rotate_kubernetes(secret_name)
        elif self.backend == SecretBackend.HASHICORP_VAULT:
            new_value = self._rotate_vault(secret_name)
        else:
            new_value = self._rotate_environment(secret_name)

        previous = os.getenv(secret_name)
        self._rotation_history[secret_name] = RotationRecord(
            secret_name=secret_name,
            previous_version=previous,
            current_version=new_value,
            rotated_at=datetime.utcnow().isoformat() + "Z",
            backend=self.backend,
        )

        if secret_name in self._schedule:
            self._schedule[secret_name] = datetime.utcnow() + self._get_default_interval()

        logger.info("Secret '%s' rotated successfully", secret_name)
        return new_value

    def schedule_rotation(self, secret_name: str, interval_days: int) -> None:
        next_rotation = datetime.utcnow() + timedelta(days=interval_days)
        self._schedule[secret_name] = next_rotation
        logger.info("Rotation scheduled for '%s' in %d days (at %s)", secret_name, interval_days, next_rotation.isoformat())

    def verify_rotation(self, secret_name: str) -> bool:
        record = self._rotation_history.get(secret_name)
        if not record:
            logger.warning("No rotation record found for secret '%s'", secret_name)
            return False

        current_env = os.getenv(secret_name)
        if current_env == record.current_version:
            logger.info("Rotation verified for secret '%s'", secret_name)
            return True

        logger.warning("Secret '%s' appears to have changed since last rotation", secret_name)
        return False

    def check_due_rotations(self) -> list[str]:
        now = datetime.utcnow()
        due = [name for name, scheduled in self._schedule.items() if scheduled <= now]
        for secret_name in due:
            logger.info("Secret '%s' is due for rotation", secret_name)
        return due

    def _rotate_kubernetes(self, secret_name: str) -> str:
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "-_"
        new_value = "".join(secrets.choice(alphabet) for _ in range(32))
        logger.debug("Generated new Kubernetes secret value for %s", secret_name)
        return new_value

    def _rotate_vault(self, secret_name: str) -> str:
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "+/"
        new_value = "".join(secrets.choice(alphabet) for _ in range(44))
        logger.debug("Generated new Vault secret value for %s", secret_name)
        return new_value

    def _rotate_environment(self, secret_name: str) -> str:
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits
        new_value = "".join(secrets.choice(alphabet) for _ in range(32))
        os.environ[secret_name] = new_value
        logger.debug("Rotated environment variable '%s'", secret_name)
        return new_value

    def _get_default_interval(self) -> timedelta:
        return timedelta(days=30)
