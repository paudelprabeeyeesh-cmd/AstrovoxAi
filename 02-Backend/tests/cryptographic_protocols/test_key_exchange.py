import pytest
from cryptographic_protocols.key_exchange import (
    DiffieHellmanKeyExchange,
    KeyEncapsulationMechanism,
    StationToStationProtocol,
)


@pytest.fixture
def alice():
    return DiffieHellmanKeyExchange()


@pytest.fixture
def bob():
    return DiffieHellmanKeyExchange()


def test_diffie_hellman_key_exchange(alice, bob):
    shared_alice = alice.generate_shared_secret(bob.public_key)
    shared_bob = bob.generate_shared_secret(alice.public_key)
    assert shared_alice == shared_bob


def test_diffie_hellman_deterministic_private_key():
    alice = DiffieHellmanKeyExchange(private_key=12345)
    bob = DiffieHellmanKeyExchange(private_key=54321)
    shared_alice = alice.generate_shared_secret(bob.public_key)
    shared_bob = bob.generate_shared_secret(alice.public_key)
    assert shared_alice == shared_bob


def test_diffie_hellman_key_derivation_context():
    alice = DiffieHellmanKeyExchange()
    shared = alice.generate_shared_secret(alice.public_key)
    key1 = DiffieHellmanKeyExchange.derive_key(shared, "context_a")
    key2 = DiffieHellmanKeyExchange.derive_key(shared, "context_b")
    assert key1 != key2
    assert len(key1) == 32
    assert len(key2) == 32


def test_key_derivation(alice, bob):
    shared_alice = alice.generate_shared_secret(bob.public_key)
    key = DiffieHellmanKeyExchange.derive_key(shared_alice, "test")
    assert len(key) == 32


def test_station_to_station_signature(alice, bob):
    shared = alice.generate_shared_secret(bob.public_key)
    sig = StationToStationProtocol.compute_signature(
        alice.private_key, alice.public_key, bob.public_key, shared
    )
    assert StationToStationProtocol.verify_signature(
        alice.private_key, alice.public_key, bob.public_key, shared, sig
    )


def test_station_to_station_invalid_signature(alice, bob):
    shared = alice.generate_shared_secret(bob.public_key)
    sig = StationToStationProtocol.compute_signature(
        alice.private_key, alice.public_key, bob.public_key, shared
    )
    tampered = b"\x00" * len(sig)
    assert not StationToStationProtocol.verify_signature(
        alice.private_key, alice.public_key, bob.public_key, shared, tampered
    )


def test_key_encapsulation_mechanism():
    pub = int.from_bytes(b"test_public", "big")
    ciphertext, key = KeyEncapsulationMechanism.encapsulate(pub)
    recovered = KeyEncapsulationMechanism.decapsulate(pub, ciphertext)
    assert key == recovered


def test_key_encapsulation_different_public_keys():
    pub1 = int.from_bytes(b"public_one", "big")
    pub2 = int.from_bytes(b"public_two", "big")
    ct1, key1 = KeyEncapsulationMechanism.encapsulate(pub1)
    ct2, key2 = KeyEncapsulationMechanism.encapsulate(pub2)
    assert key1 != key2
    assert len(key1) == 32
    assert len(key2) == 32
