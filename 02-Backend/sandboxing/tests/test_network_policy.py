import numpy as np

from sandboxing.network_policy import NetworkPolicy


def test_default_deny_blocks_unlisted():
    policy = NetworkPolicy(allowlist_domains=frozenset({"example.com"}))
    assert policy.check_egress("evil.com") is False


def test_allowlist_permits_domain():
    policy = NetworkPolicy(allowlist_domains=frozenset({"example.com"}))
    assert policy.check_egress("example.com") is True


def test_allowlist_permits_subdomain():
    policy = NetworkPolicy(allowlist_domains=frozenset({"example.com"}))
    assert policy.check_egress("api.example.com") is True


def test_disable_default_deny_allows_all():
    policy = NetworkPolicy(default_deny=False, allowlist_domains=frozenset())
    assert policy.check_egress("anything.com") is True


def test_credential_redaction():
    policy = NetworkPolicy(credential_isolation=True)
    sanitized = policy.isolate_credentials("connect user=admin password=secret")
    assert "secret" not in sanitized
    assert "[REDACTED]" in sanitized


def test_numpy_batch_egress():
    policy = NetworkPolicy(allowlist_domains=frozenset({"safe.io"}))
    targets = np.array(["safe.io", "unsafe.io", "sub.safe.io", "evil.net"])
    expected = np.array([True, False, True, False])
    results = np.array([policy.check_egress(t) for t in targets])
    np.testing.assert_array_equal(results, expected)
