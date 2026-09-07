"""Ecosystem base exceptions."""

from __future__ import annotations


class EcosystemError(Exception):
    """Base exception for ecosystem operations."""

    def __init__(self, message: str = "", code: str = "ecosystem_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class RegistryError(EcosystemError):
    """Registry operation failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="registry_error")


class LookupError(EcosystemError):
    """Lookup operation failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="lookup_error")


class CompatibilityError(EcosystemError):
    """Compatibility check failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="compatibility_error")


class RecoveryError(EcosystemError):
    """Recovery operation failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="recovery_error")


class ValidationError(EcosystemError):
    """Validation operation failed."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message, code="validation_error")
