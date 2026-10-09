from advanced_security.homomorphic_encryption import HomomorphicKeyPair, PaillierKeyPair


def test_homomorphic_keypair() -> None:
    kp = HomomorphicKeyPair(64)
    c1 = kp.encrypt(5)
    c2 = kp.encrypt(3)
    aggregated = kp.aggregate(c1, c2)
    decrypted = kp.decrypt(aggregated)
    assert decrypted == 8


def test_homomorphic_decrypt_identity() -> None:
    kp = HomomorphicKeyPair(64)
    for v in (0, 1, 2, 3):
        assert kp.decrypt(kp.encrypt(v)) == v


def test_paillier_keypair() -> None:
    kp = PaillierKeyPair()
    c1 = kp.encrypt(4)
    c2 = kp.encrypt(6)
    summed = kp.add(c1, c2)
    result = kp.decrypt(summed)
    assert result == 10


def test_paillier_decrypt_matches() -> None:
    kp = PaillierKeyPair()
    for v in (0, 1, 2, 3, 4, 5, 6, 7):
        assert kp.decrypt(kp.encrypt(v)) == v
