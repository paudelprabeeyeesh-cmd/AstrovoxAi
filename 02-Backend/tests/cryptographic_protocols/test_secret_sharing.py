import pytest
from cryptographic_protocols.secret_sharing import (
    BlakleySecretSharing,
    ShamirSecretSharing,
)


def test_shamir_split_reconstruct():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345"
    shares = sss.split(secret)
    assert len(shares) == 5
    reconstructed = sss.reconstruct(shares[:3])
    assert reconstructed == secret


def test_shamir_insufficient_shares():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345"
    shares = sss.split(secret)
    with pytest.raises(ValueError):
        sss.reconstruct(shares[:2])


def test_shamir_different_shares_different_result():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345"
    shares1 = sss.split(secret)
    shares2 = sss.split(secret)
    assert shares1 != shares2
    assert sss.reconstruct(shares1[:3]) == secret
    assert sss.reconstruct(shares2[:3]) == secret


def test_blakley_split_reconstruct():
    bss = BlakleySecretSharing(threshold=3, total_shares=5)
    secret = b"blakley12345"
    shares = bss.split(secret)
    assert len(shares) == 5
    reconstructed = bss.reconstruct(shares[:3])
    assert reconstructed == secret


def test_blakley_insufficient_shares():
    bss = BlakleySecretSharing(threshold=3, total_shares=5)
    secret = b"blakley12345"
    shares = bss.split(secret)
    with pytest.raises(ValueError):
        bss.reconstruct(shares[:2])
