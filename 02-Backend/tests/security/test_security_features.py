"""Tests for security features: brute-force, password strength, token revocation,
refresh token rotation, IP filter, UA analytics, anomaly detection, audit immutability.
"""

from __future__ import annotations

import time
import pytest

from app.security.brute_force_protection import BruteForceProtection, BruteForceConfig
from app.security.password_strength import PasswordStrengthEnforcer, password_enforcer
from app.security.token_revocation import TokenRevocationList, token_revocation_list
from app.security.refresh_token_rotation import RefreshTokenRotation
from app.security.password_reset import SecurePasswordReset, secure_password_reset
from app.security.audit_immutable import ImmutableAuditStore
from app.security.webhook_signing import WebhookSigner
from app.security.ip_filter import IPFilter
from app.security.user_agent_analytics import UserAgentAnalyzer, user_agent_analyzer
from app.security.anomaly_alerts import AuthAnomalyDetector, AuthEvent, auth_anomaly_detector


class TestBruteForceProtection:
    def test_record_failure_and_lockout(self):
        config = BruteForceConfig(max_attempts=3, window_seconds=60.0, lockout_seconds=10.0)
        bf = BruteForceProtection(config)
        identity = "test@example.com"

        for _ in range(2):
            allowed, _ = bf.record_failure(identity)
            assert allowed is True

        allowed, remaining = bf.record_failure(identity)
        assert allowed is False
        assert remaining is not None and remaining > 0

    def test_remaining_attempts(self):
        config = BruteForceConfig(max_attempts=5, window_seconds=60.0, lockout_seconds=10.0)
        bf = BruteForceProtection(config)
        identity = "test2@example.com"

        for _ in range(2):
            bf.record_failure(identity)
        assert bf.remaining_attempts(identity) == 3

    def test_record_success_resets(self):
        config = BruteForceConfig(max_attempts=3, window_seconds=60.0, lockout_seconds=10.0)
        bf = BruteForceProtection(config)
        identity = "test3@example.com"

        bf.record_failure(identity)
        bf.record_success(identity)
        assert bf.remaining_attempts(identity) == 3


class TestPasswordStrength:
    def test_weak_password_rejected(self):
        result = password_enforcer.validate("short")
        assert result.valid is False
        assert result.score < 5

    def test_common_password_rejected(self):
        result = password_enforcer.validate("password123")
        assert result.valid is False

    def test_strong_password_accepted(self):
        result = password_enforcer.validate("Str0ng!Pass#2024")
        assert result.valid is True

    def test_entropy_calculation(self):
        enforcer = PasswordStrengthEnforcer(min_entropy=30.0)
        result = enforcer.validate("aB3!dEf7@GhI9")
        assert result.entropy >= 30.0


class TestTokenRevocation:
    def test_revoke_and_check(self):
        tlr = TokenRevocationList()
        tlr.revoke("jti-1", "user-1", time.time() + 3600, reason="logout")
        assert tlr.is_revoked("jti-1") is True
        assert tlr.is_revoked("jti-unknown") is False

    def test_revoke_all_for_user(self):
        tlr = TokenRevocationList()
        tlr.revoke("jti-a", "user-x", time.time() + 3600)
        tlr.revoke("jti-b", "user-y", time.time() + 3600)
        tlr.revoke_all_for_user("user-y", ["jti-c", "jti-d"], reason="password_change")
        assert tlr.is_revoked("jti-a") is True
        assert tlr.is_revoked("jti-b") is True
        assert tlr.is_revoked("jti-c") is True


class TestRefreshTokenRotation:
    def test_rotate_success(self):
        rtr = RefreshTokenRotation(rotation_lifetime_seconds=3600.0)
        user_id = "user-1"
        old_token = rtr.generate(user_id)
        new_token, rotated = rtr.rotate(old_token, user_id)
        assert rotated is True
        assert new_token != old_token
        assert rtr.validate(new_token, user_id) is True

    def test_reuse_detected(self):
        rtr = RefreshTokenRotation(rotation_lifetime_seconds=3600.0)
        user_id = "user-1"
        old_token = rtr.generate(user_id)
        rtr.rotate(old_token, user_id)
        with pytest.raises(ValueError, match="reuse detected"):
            rtr.rotate(old_token, user_id)


class TestPasswordReset:
    def test_create_and_consume(self):
        pr = SecurePasswordReset(ttl_seconds=3600.0)
        raw = pr.create_token("user@example.com")
        assert pr.consume_token(raw, "user@example.com") is True
        assert pr.consume_token(raw, "user@example.com") is False

    def test_expired_token_rejected(self):
        pr = SecurePasswordReset(ttl_seconds=-1.0)
        raw = pr.create_token("user@example.com")
        assert pr.consume_token(raw, "user@example.com") is False


class TestAuditImmutability:
    def test_chain_integrity(self):
        store = ImmutableAuditStore()
        store.record("actor-1", "login", "user", "success", "")
        store.record("actor-1", "logout", "user", "success", "")
        valid, bad_idx = store.verify_chain()
        assert valid is True
        assert bad_idx is None

    def test_query_by_actor(self):
        store = ImmutableAuditStore()
        store.record("alice", "login", "user", "success", "")
        store.record("bob", "login", "user", "success", "")
        store.record("alice", "update", "profile", "success", "")
        results = store.query(actor="alice")
        assert len(results) == 2


class TestWebhookSigning:
    def test_sign_and_verify(self):
        signer = WebhookSigner("test-secret-key")
        payload = b'{"event": "test"}'
        sig = signer.sign(payload)
        assert signer.verify(payload, sig) is True

    def test_tampered_payload_rejected(self):
        signer = WebhookSigner("test-secret-key")
        payload = b'{"event": "test"}'
        sig = signer.sign(payload)
        assert signer.verify(b'{"event": "tampered"}', sig) is False


class TestIPFilter:
    def test_denylist_blocks(self):
        f = IPFilter(denylist=["10.0.0.0/8"])
        allowed, reason = f.check("10.1.2.3")
        assert allowed is False
        assert reason == "denylisted"

    def test_allowlist_permits(self):
        f = IPFilter(allowlist=["192.168.1.0/24"])
        allowed, reason = f.check("192.168.1.5")
        assert allowed is True

    def test_not_allowlisted_rejected(self):
        f = IPFilter(allowlist=["192.168.1.0/24"])
        allowed, reason = f.check("10.0.0.1")
        assert allowed is False
        assert reason == "not_allowlisted"


class TestUserAgentAnalytics:
    def test_record_valid_ua(self):
        ua = UserAgentAnalyzer()
        allowed, reason = ua.record("Mozilla/5.0")
        assert allowed is True

    def test_block_bot_ua(self):
        ua = UserAgentAnalyzer()
        ua.record("python-requests/2.28")
        assert "python-requests/2.28" in ua.blocked_agents()

    def test_missing_ua_rejected(self):
        ua = UserAgentAnalyzer()
        allowed, reason = ua.record("")
        assert allowed is False
        assert reason == "missing_user_agent"


class TestAnomalyAlerts:
    def test_rapid_auth_detection(self):
        detector = AuthAnomalyDetector()
        base_time = time.time()
        for i in range(15):
            detector.record(AuthEvent(
                user_id="user-1", ip="1.2.3.4", country=None,
                user_agent="test", timestamp=base_time + i,
            ))
        alerts = detector.record(AuthEvent(
            user_id="user-1", ip="1.2.3.4", country=None,
            user_agent="test", timestamp=base_time + 16,
        ))
        alert_types = [a.alert_type for a in alerts]
        assert "rapid_auth" in alert_types
