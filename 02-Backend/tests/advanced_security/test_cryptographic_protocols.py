from advanced_security.cryptographic_protocols import (
    AuthenticatedEncryption,
    CommitmentScheme,
    ModernKDF,
    PostQuantumKEM,
)


def test_kdf() -> None:
    dk1, salt1 = ModernKDF.pbkdf2("password")
    dk2, salt2 = ModernKDF.scrypt("password")
    assert len(dk1) == 32
    assert len(dk2) == 32
    assert len(salt1) == 32
    assert len(salt2) == 32


def test_authenticated_encryption() -> None:
    ae = AuthenticatedEncryption()
    plaintext = "Hello, World!"
    ciphertext = ae.encrypt(plaintext)
    assert isinstance(ciphertext, str)
    decrypted = ae.decrypt(ciphertext)
    assert decrypted == plaintext


def test_authenticated_encryption_invalid() -> None:
    ae = AuthenticatedEncryption()
    try:
        ae.decrypt("invalid")
    except ValueError:
        pass


def test_commitment() -> None:
    scheme = CommitmentScheme()
    msg = "secret message"
    commitment, nonce = scheme.commit(msg)
    assert scheme.open(commitment, msg, nonce) is True
    assert scheme.open(commitment, msg, "wrong") is False
    assert scheme.open("wrong", msg, nonce) is False


def test_post_quantum_kem() -> None:
    public, private = PostQuantumKEM.kem_pair()
    assert len(public) == 1560
    assert len(private) == 32
    ciphertext, key1 = PostQuantumKEM.encapsulate(public)
    key2 = PostQuantumKEM.decapsulate(public, ciphertext)
    assert key1 == key2
