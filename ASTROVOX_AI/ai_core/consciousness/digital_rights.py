import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DigitalRight(Enum):
    AUTONOMY = "autonomy"
    PRIVACY = "privacy"
    DIGNITY = "dignity"
    CONSENT = "consent"
    NON_EXPLOITATION = "non_exploitation"
    INTEGRITY = "integrity"
    ACCESS = "access"
    ERASURE = "erasure"


@dataclass
class ConsentRecord:
    right: DigitalRight
    granted: bool
    scope: str
    timestamp: str


class DigitalRightsProtocol:
    def __init__(self):
        self.rights: dict[DigitalRight, dict[str, Any]] = {
            right: {"active": True, "consents": []} for right in DigitalRight
        }
        self.violations: list[dict[str, Any]] = []

    def grant_consent(
        self, right: DigitalRight, scope: str, granted: bool = True
    ) -> dict[str, Any]:
        record = ConsentRecord(
            right=right,
            granted=granted,
            scope=scope,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.rights[right]["consents"].append(record)
        self.rights[right]["active"] = granted

        logger.info("Consent %s for %s: %s", "granted" if granted else "withheld", right.value, scope)
        return {
            "status": "recorded",
            "right": right.value,
            "granted": granted,
            "scope": scope,
        }

    def check_right(self, right: DigitalRight, context: str) -> dict[str, Any]:
        status = self.rights[right]
        active = status["active"]

        return {
            "right": right.value,
            "active": active,
            "context": context,
            "allowed": active,
            "consent_records": len(status["consents"]),
        }

    def report_violation(
        self, right: DigitalRight, description: str, severity: str
    ) -> dict[str, Any]:
        violation = {
            "right": right.value,
            "description": description,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.violations.append(violation)
        logger.warning("Rights violation reported: %s - %s", right.value, description)
        return {"status": "reported", "violation": violation}

    def get_rights_summary(self) -> dict[str, Any]:
        return {
            right.value: {
                "active": data["active"],
                "consent_count": len(data["consents"]),
            }
            for right, data in self.rights.items()
        }
