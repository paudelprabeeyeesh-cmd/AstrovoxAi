import hashlib
import pytest
from cryptographic_protocols.secret_sharing import (
    BlakleySecretSharing,
    ShamirSecretSharing,
)


def test_shamir_split_reconstruct():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345" + b"\x00" * 21
    shares = sss.split(secret)
    assert len(shares) == 5
    reconstructed = sss.reconstruct(shares[:3])
    assert reconstructed == secret


def test_shamir_threshold_two():
    sss = ShamirSecretSharing(threshold=2, total_shares=3)
    secret = b"secret12345" + b"\x00" * 21
    shares = sss.split(secret)
    assert len(shares) == 3
    assert sss.reconstruct(shares[:2]) == secret


def test_shamir_insufficient_shares():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345" + b"\x00" * 21
    shares = sss.split(secret)
    with pytest.raises(ValueError):
        sss.reconstruct(shares[:2])


def test_shamir_invalid_params():
    with pytest.raises(ValueError):
        ShamirSecretSharing(threshold=1, total_shares=3)
    with pytest.raises(ValueError):
        ShamirSecretSharing(threshold=3, total_shares=2)


def test_shamir_different_shares_different_result():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345" + b"\x00" * 21
    shares1 = sss.split(secret)
    shares2 = sss.split(secret)
    assert shares1 != shares2
    assert sss.reconstruct(shares1[:3]) == secret
    assert sss.reconstruct(shares2[:3]) == secret


def test_shamir_verify_share():
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    secret = b"secret12345" + b"\x00" * 21
    commitment = hashlib.sha256(secret).digest()
    shares = sss.split(secret)
    share = shares[0]
    assert ShamirSecretSharing.verify_share(share, commitment)
    tampered = (share[0], share[1] + 1)
    assert not ShamirSecretSharing.verify_share(tampered, commitment)


def test_blakley_split_reconstruct():
    bss = BlakleySecretSharing(threshold=3, total_shares=5)
    secret = b"blakley12345" + b"\x00" * 21
    shares = bss.split(secret)
    assert len(shares) == 5
    reconstructed = bss.reconstruct(shares[:3])
    assert reconstructed == secret


def test_blakley_threshold_two():
    bss = BlakleySecretSharing(threshold=2, total_shares=3)
    secret = b"blakley12345" + b"\x00" * 21
    shares = bss.split(secret)
    assert len(shares) == 3
    assert bss.reconstruct(shares[:2]) == secret


def test_blakley_insufficient_shares():
    bss = BlakleySecretSharing(threshold=3, total_shares=5)
    secret = b"blakley12345" + b"\x00" * 21
    shares = bss.split(secret)
    with pytest.raises(ValueError):
        bss.reconstruct(shares[:2])


def test_blakley_invalid_params():
    with pytest.raises(ValueError):
        BlakleySecretSharing(threshold=1, total_shares=3)
    with pytest.raises(ValueError):
        BlakleySecretSharing(threshold=3, total_shares=2)


def test_blakley_different_shares_different_result():
    bss = BlakleySecretSharing(threshold=3, total_shares=5)
    secret = b"blakley12345" + b"\x00" * 21
    shares1 = bss.split(secret)
    shares2 = bss.split(secret)
    assert shares1 != shares2
    assert bss.reconstruct(shares1[:3]) == secret
    assert bss.reconstruct(shares2[:3]) == secret
