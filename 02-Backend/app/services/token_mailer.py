"""Single-use token delivery (G1.1).

Verification, reset, and magic-link tokens are account-takeover
credentials: whoever holds one owns the account until it is used or
expires. They are therefore never returned in an API response and never
logged. The only channel that carries them is email.

This module owns that boundary. Every caller gets a token recipient from
``deliver_token`` and nothing else; the raw token is discarded by the
caller's caller and only reaches ``Mailer``.

Test wiring: ``set_mailer()`` swaps in a recording mailer, so a test can
assert the email channel was used and no response contained the token,
without any SMTP server.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

# A token left in an inbox is a standing invitation. The verifier is
# single-use, so this only bounds how long the invitation waits.
VERIFY_TTL_HOURS = 24
RESET_TTL_HOURS = 1
MAGIC_LINK_TTL_MINUTES = 15


class Mailer(Protocol):
    def send_token(self, email: str, token: str, purpose: str, ttl_label: str) -> bool:
        ...


class NullMailer:
    """Delivery target for environments with no SMTP configured.

    The token is deliberately not logged. If a deployment forgets to
    configure SMTP, the operator must find out that mail is not being
    delivered from the startup check and the returned False, not from a
    token written into an app log.
    """

    def send_token(self, email: str, token: str, purpose: str, ttl_label: str) -> bool:
        logger.warning(
            "token_mailer.not_configured purpose=%s email_domain=%s ttl=%s "
            "(no SMTP configured; token NOT sent and NOT logged)",
            purpose,
            email.split("@")[-1] if "@" in email else "unknown",
            ttl_label,
        )
        return False


class SMTPMailer:
    """SMTP delivery. Reads settings at call time so tests and config
    reloads behave the same."""

    def __init__(self) -> None:
        from app.config import settings

        self._settings = settings

    def send_token(self, email: str, token: str, purpose: str, ttl_label: str) -> bool:
        host = getattr(self._settings, "smtp_host", "") or ""
        port = int(getattr(self._settings, "smtp_port", 587) or 587)
        user = getattr(self._settings, "smtp_user", "") or ""
        password = getattr(self._settings, "smtp_password", "") or ""
        sender = getattr(self._settings, "smtp_from", "") or user
        use_tls = bool(getattr(self._settings, "smtp_tls", True))

        if not host or not sender:
            logger.warning("token_mailer.incomplete_config purpose=%s", purpose)
            return False

        subject = {
            "verify_email": "Confirm your email address",
            "reset_password": "Reset your password",
            "magic_link": "Your sign-in link",
        }.get(purpose, "Your security code")

        message = EmailMessage()
        message["From"] = sender
        message["To"] = email
        message["Subject"] = subject
        message.set_content(
            f"Use this code: {token}\n\n"
            f"It expires in {ttl_label}. If you did not request it, ignore this email."
        )

        try:
            with smtplib.SMTP(host, port, timeout=10) as client:
                if use_tls:
                    client.starttls()
                if user and password:
                    client.login(user, password)
                client.send_message(message)
        except Exception:  # noqa: BLE001 - delivery failure must not leak token or host detail
            logger.exception("token_mailer.send_failed purpose=%s", purpose)
            return False
        return True


class RecordingMailer:
    """Test mailer: records what would have been sent, never exposes it."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send_token(self, email: str, token: str, purpose: str, ttl_label: str) -> bool:
        self.sent.append({
            "email": email,
            "purpose": purpose,
            "ttl_label": ttl_label,
            "token_len": len(token),
            "token_prefix": token[:4],
        })
        return True

    def tokens_for(self, purpose: str) -> list[dict]:
        return [m for m in self.sent if m["purpose"] == purpose]


_mailer: Optional[Mailer] = None


def get_mailer() -> Mailer:
    global _mailer
    if _mailer is None:
        _mailer = _default_mailer()
    return _mailer


def _default_mailer() -> Mailer:
    from app.config import settings

    if getattr(settings, "smtp_host", ""):
        return SMTPMailer()
    return NullMailer()


def set_mailer(mailer: Optional[Mailer]) -> None:
    """Install a mailer. Pass None to restore the configured default."""
    global _mailer
    _mailer = mailer


_TTL_LABELS = {
    "verify_email": f"{VERIFY_TTL_HOURS} hours",
    "reset_password": f"{RESET_TTL_HOURS} hour",
    "magic_link": f"{MAGIC_LINK_TTL_MINUTES} minutes",
}


def deliver_token(email: str, token: str, purpose: str) -> bool:
    """Send a single-use token to its owner.

    Returns True when the mailer accepted delivery. A False means the
    caller must not treat the account action as complete.
    """
    ttl_label = _TTL_LABELS.get(purpose, "a limited time")
    return get_mailer().send_token(email, token, purpose, ttl_label)


def token_delivery_configured() -> bool:
    """Startup check: True when a real SMTP host is configured."""
    from app.config import settings

    return bool(getattr(settings, "smtp_host", ""))
