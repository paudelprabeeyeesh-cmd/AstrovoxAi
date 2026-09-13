import pytest
from app.core.pii import detect_pii, redact_pii, restore_pii, has_pii


def test_detect_pii_email():
    text = "Contact me at john@example.com"
    detected = detect_pii(text)
    assert "email" in detected


def test_detect_pii_phone():
    text = "Call 555-123-4567"
    detected = detect_pii(text)
    assert "phone" in detected


def test_detect_pii_ssn():
    text = "SSN: 123-45-6789"
    detected = detect_pii(text)
    assert "ssn" in detected


def test_detect_pii_credit_card():
    text = "Card: 4111-1111-1111-1111"
    detected = detect_pii(text)
    assert "credit_card" in detected


def test_detect_pii_none():
    text = "Hello world"
    detected = detect_pii(text)
    assert len(detected) == 0


def test_redact_pii():
    text = "Email: john@example.com, Phone: 555-123-4567"
    redacted = redact_pii(text)
    assert "john@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted


def test_has_pii_true():
    assert has_pii("john@example.com") is True


def test_has_pii_false():
    assert has_pii("hello world") is False
