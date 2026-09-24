from advanced_security.zero_trust import Identity, PBACEngine, PolicyEngine, ZeroTrustAuthenticator


def test_identity() -> None:
    subject = Identity(subject="user", attributes={"role": "admin"})
    assert subject.subject == "user"


def test_challenge_verification() -> None:
    auth = ZeroTrustAuthenticator("secret")
    subject = "user"
    challenge = auth.challenge(subject)
    result = auth.verify(subject, challenge["nonce"], challenge["signature"])
    assert result.success is True


def test_replay_attacked() -> None:
    auth = ZeroTrustAuthenticator("secret")
    challenge = auth.challenge("user")
    auth.verify("user", challenge["nonce"], challenge["signature"])
    result = auth.verify("user", challenge["nonce"], challenge["signature"])
    assert result.success is False
    assert result.evidence["reason"] == "replay"


def test_policy_engine() -> None:
    engine = PolicyEngine()
    engine.add_rule("allow", ["read"], "owner", "alice")
    subject = Identity(subject="alice")
    resource = {"owner": "alice"}
    result = engine.evaluate(subject, "read", resource)
    assert result.success is True


def test_policy_implicit_deny() -> None:
    engine = PolicyEngine()
    subject = Identity(subject="alice")
    resource = {"owner": "bob"}
    result = engine.evaluate(subject, "write", resource)
    assert result.success is False
    assert result.evidence["reason"] == "implicit_deny"


def test_pbac_engine() -> None:
    pbac = PBACEngine()
    subject = Identity(subject="user", attributes={"role": "viewer"}, roles=["viewer"])
    resource = Resource(id="r1", type="file")
    pbac.add_policy("allow", [{"has_role": "viewer"}, {"resource_type": "file"}])
    assert pbac.evaluate(subject, resource, "read", {}) is True
