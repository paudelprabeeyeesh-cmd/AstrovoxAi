import hashlib
from advanced_security.post_quantum_crypto import (
    HashBasedSignature,
    LatticeSignature,
    PostQuantumCrypto,
    PostQuantumKEM,
)


def test_kem_keypair() -> None:
    public, private = PostQuantumKEM.generate_keypair()
    assert isinstance(public, bytes)
    assert isinstance(private, bytes)
    assert len(private) == 32


def test_kem_encapsulate_decapsulate() -> None:
    public, private = PostQuantumKEM.generate_keypair()
    ciphertext, key1 = PostQuantumKEM.encapsulate(public)
    key2 = PostQuantumKEM.decapsulate(public, ciphertext, private)
    assert key1 == key2


def test_hash_signature_sign_verify() -> None:
    scheme = HashBasedSignature(height=8)
    public = scheme.public_key()
    path = scheme.sign(b"message", index=1)
    assert HashBasedSignature.verify(public, b"message", 1, path) is True
    assert HashBasedSignature.verify(public, b"other", 1, path) is False


def test_lattice_signature() -> None:
    private = b"private_key_seed"
    public = private
    sig = LatticeSignature.sign(private, b"message")
    assert LatticeSignature.verify(public, b"message", sig) is True
    assert LatticeSignature.verify(public, b"other", sig) is False


def test_postquantum_unified_kem() -> None:
    public, private = PostQuantumCrypto.kem_keypair()
    ciphertext, key1 = PostQuantumCrypto.kem_encaps(public)
    key2 = PostQuantumCrypto.kem_decaps(public, ciphertext, private)
    assert key1 == key2


def test_postquantum_hash_sign_verify() -> None:
    scheme = HashBasedSignature(height=8)
    public = scheme.public_key()
    path = scheme.sign(b"msg", index=2)
    assert HashBasedSignature.verify(public, b"msg", 2, path) is True
