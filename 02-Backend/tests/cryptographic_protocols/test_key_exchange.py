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


def test_key_encapsulation_mechanism():
    pub = int.from_bytes(b"test_public", "big")
    ciphertext, key = KeyEncapsulationMechanism.encapsulate(pub)
    recovered = KeyEncapsulationMechanism.decapsulate(pub, ciphertext)
    assert key == recovered
