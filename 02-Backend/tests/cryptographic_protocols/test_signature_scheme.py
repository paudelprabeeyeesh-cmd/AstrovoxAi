import pytest
from cryptographic_protocols.signature_scheme import (
    HMACSignatureScheme,
    HashBasedSignature,
    MerkleSignatureScheme,
)


def test_hmac_signature_sign_verify():
    scheme = HMACSignatureScheme()
    message = b"hello world"
    signature = scheme.sign(message)
    assert scheme.verify(message, signature)
    assert not scheme.verify(b"other", signature)


def test_hmac_signature_key_reuse():
    key = b"shared_secret"
    scheme1 = HMACSignatureScheme(key)
    scheme2 = HMACSignatureScheme(key)
    message = b"shared message"
    signature = scheme1.sign(message)
    assert scheme2.verify(message, signature)


def test_hash_based_signature():
    private_key, public_key = HashBasedSignature.generate_keypair()
    message = b"sign me"
    signature = HashBasedSignature.sign(private_key, message)
    assert HashBasedSignature.verify(public_key, message, signature)
    assert not HashBasedSignature.verify(public_key, b"other", signature)


def test_hash_based_signature_wrong_key():
    private_key, public_key = HashBasedSignature.generate_keypair()
    wrong_private_key, _ = HashBasedSignature.generate_keypair()
    message = b"sign me"
    signature = HashBasedSignature.sign(private_key, message)
    assert not HashBasedSignature.verify(wrong_private_key, message, signature)


def test_merkle_signature():
    mss = MerkleSignatureScheme(height=4)
    message = b"merkle message"
    private_key, auth_path = mss.sign(0, message)
    assert MerkleSignatureScheme.verify(mss.public_key, 0, message, private_key, auth_path)


def test_merkle_signature_invalid_index():
    mss = MerkleSignatureScheme(height=4)
    with pytest.raises(ValueError):
        mss.sign(100, b"message")


def test_merkle_signature_wrong_message():
    mss = MerkleSignatureScheme(height=4)
    private_key, auth_path = mss.sign(0, b"correct")
    assert not MerkleSignatureScheme.verify(mss.public_key, 0, b"wrong", private_key, auth_path)


def test_merkle_signature_different_indices():
    mss = MerkleSignatureScheme(height=4)
    message = b"merkle message"
    _, auth_path_0 = mss.sign(0, message)
    _, auth_path_1 = mss.sign(1, message)
    assert MerkleSignatureScheme.verify(mss.public_key, 0, message, mss._private_keys[0], auth_path_0)
    assert MerkleSignatureScheme.verify(mss.public_key, 1, message, mss._private_keys[1], auth_path_1)


def test_merkle_public_key_length():
    mss = MerkleSignatureScheme(height=4)
    assert len(mss.public_key) == 32
