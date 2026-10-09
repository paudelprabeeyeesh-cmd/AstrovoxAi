from advanced_security.secure_multiparty import OTProtocol, SecretSharing


def test_secret_sharing_split() -> None:
    ss = SecretSharing(threshold=3, parts=5)
    shares = ss.split(42)
    assert len(shares) == 5
    assert len({s[0] for s in shares}) == 5


def test_secret_sharing_recover() -> None:
    ss = SecretSharing(threshold=3, parts=5)
    secret = 12345
    shares = ss.split(secret)
    recovered = ss.recover(shares[:3])
    assert recovered == secret % ss._prime


def test_secret_sharing_different_subsets() -> None:
    ss = SecretSharing(threshold=3, parts=5)
    secret = 9999
    shares = ss.split(secret)
    recovered1 = ss.recover([shares[0], shares[2], shares[4]])
    recovered2 = ss.recover([shares[1], shares[2], shares[3]])
    assert recovered1 == secret % ss._prime
    assert recovered2 == secret % ss._prime


def test_ot_choose() -> None:
    messages = [10, 20, 30, 40]
    for i in range(len(messages)):
        result = OTProtocol.choose_choice_bit(messages, i)
        assert result == messages[i]


def test_secret_sharing_large_prime() -> None:
    ss = SecretSharing(threshold=4, parts=7)
    shares = ss.split(2 ** 20)
    recovered = ss.recover(shares[:4])
    assert recovered == (2 ** 20) % ss._prime
