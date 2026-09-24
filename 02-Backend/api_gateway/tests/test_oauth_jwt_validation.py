import time
import pytest
import numpy as np
from api_gateway.oauth_jwt_validation import (
    JWTValidator,
    KeyRotationManager,
    TokenPayload,
    KeyStatus,
)


class TestKeyRotationManager:
    def test_initial_key_generated(self):
        mgr = KeyRotationManager(rotation_interval=9999.0)
        key = mgr.get_active_key()
        assert key.key_id
        assert key.secret
        assert key.status == KeyStatus.ACTIVE

    def test_active_key_consistent(self):
        mgr = KeyRotationManager(rotation_interval=9999.0)
        k1 = mgr.active_key_id
        k2 = mgr.active_key_id
        assert k1 == k2

    def test_get_key_returns_active(self):
        mgr = KeyRotationManager(rotation_interval=9999.0)
        kid = mgr.active_key_id
        key = mgr.get_key(kid)
        assert key is not None
        assert key.status == KeyStatus.ACTIVE

    def test_get_unknown_key_returns_none(self):
        mgr = KeyRotationManager(rotation_interval=9999.0)
        assert mgr.get_key("nonexistent") is None

    def test_rotate_keys_changes_active(self):
        mgr = KeyRotationManager(rotation_interval=9999.0)
        old_kid = mgr.active_key_id
        new_kid = mgr.rotate_keys()
        assert new_kid != old_kid
        assert mgr.active_key_id == new_kid

    def test_rotated_key_status_changes(self):
        mgr = KeyRotationManager(rotation_interval=9999.0, overlap_grace=0.2)
        old_kid = mgr.active_key_id
        mgr.rotate_keys()
        old_key = mgr.get_key(old_kid)
        assert old_key.status == KeyStatus.ROTATING
        time.sleep(0.3)
        old_key = mgr.get_key(old_kid)
        assert old_key is None or old_key.status == KeyStatus.REVOKED

    def test_old_key_still_valid_during_grace(self):
        mgr = KeyRotationManager(rotation_interval=9999.0, overlap_grace=5.0)
        old_kid = mgr.active_key_id
        mgr.rotate_keys()
        old_key = mgr.get_key(old_kid)
        assert old_key is not None
        assert old_key.status != KeyStatus.REVOKED

    def test_multiple_rotations(self):
        mgr = KeyRotationManager(rotation_interval=9999.0, overlap_grace=0.2)
        kids = [mgr.rotate_keys() for _ in range(5)]
        assert len(set(kids)) == 5
        time.sleep(0.3)
        for kid in kids[:-1]:
            key = mgr.get_key(kid)
            assert key is None or key.status == KeyStatus.REVOKED


class TestJWTValidator:
    def test_create_and_validate_token(self):
        validator = JWTValidator()
        token, kid = validator.create_token("user-1", {"read", "write"})
        payload = validator.validate_token(token, required_scopes={"read"})
        assert payload.sub == "user-1"
        assert "read" in payload.scopes
        assert "write" in payload.scopes

    def test_validate_token_missing_scope_raises(self):
        validator = JWTValidator()
        token, _ = validator.create_token("user-1", {"read"})
        with pytest.raises(ValueError, match="Missing required scopes"):
            validator.validate_token(token, required_scopes={"write"})

    def test_validate_token_bad_format(self):
        validator = JWTValidator()
        with pytest.raises(ValueError):
            validator.validate_token("not-a-token")

    def test_validate_expired_token(self):
        validator = JWTValidator(leeway=0.0)
        token, _ = validator.create_token("user-1", set(), ttl=-1.0)
        with pytest.raises(ValueError, match="expired"):
            validator.validate_token(token)

    def test_validate_token_invalid_signature(self):
        validator = JWTValidator()
        token, _ = validator.create_token("user-1", set())
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsig"
        with pytest.raises(ValueError, match="signature"):
            validator.validate_token(tampered)

    def test_revoke_token_blocks_validation(self):
        validator = JWTValidator()
        token, _ = validator.create_token("user-1", set())
        payload_before = validator.validate_token(token)
        validator.revoke_token(payload_before.jti)
        with pytest.raises(ValueError, match="revoked"):
            validator.validate_token(token)

    def test_multiple_tokens_independent(self):
        validator = JWTValidator()
        tokens = [validator.create_token(f"user-{i}", {"read"})[0] for i in range(10)]
        for i, tok in enumerate(tokens):
            payload = validator.validate_token(tok)
            assert payload.sub == f"user-{i}"

    def test_key_rotation_validates_old_token(self):
        rotation_mgr = KeyRotationManager(rotation_interval=9999.0, overlap_grace=10.0)
        validator = JWTValidator(rotation_manager=rotation_mgr)
        token, old_kid = validator.create_token("user-1", {"read"})
        new_kid = rotation_mgr.rotate_keys()
        assert old_kid != new_kid
        payload = validator.validate_token(token, required_scopes={"read"})
        assert payload.sub == "user-1"

    def test_numpy_token_latency_distribution(self):
        validator = JWTValidator()
        n = 200
        subjects = [f"user-{i % 50}" for i in range(n)]
        scopes_list = [{"read", "write"} for _ in range(n)]
        latencies = []
        for sub, scopes in zip(subjects, scopes_list):
            start = time.time()
            token, _ = validator.create_token(sub, scopes)
            validator.validate_token(token, required_scopes={"read"})
            latencies.append(time.time() - start)
        arr = np.array(latencies)
        assert arr.mean() < 0.05
        assert arr.max() < 0.5
        assert arr.std() < 0.05

    def test_jwt_issuer_validation(self):
        validator = JWTValidator(default_issuer="astrovox")
        token, _ = validator.create_token("u1", set(), issuer="astrovox")
        payload = validator.validate_token(token)
        assert payload.iss == "astrovox"

    def test_concurrent_token_creation(self):
        validator = JWTValidator()
        import threading
        results = []
        errors = []

        def worker(i):
            try:
                tok, _ = validator.create_token(f"u{i}", {"read"})
                results.append(validator.validate_token(tok))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(results) == 50
