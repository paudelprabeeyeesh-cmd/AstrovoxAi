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


def test_merkle_signature():
    mss = MerkleSignatureScheme(height=4)
    message = b"merkle message"
    private_key, auth_path = mss.sign(0, message)
    assert MerkleSignatureScheme.verify(mss.public_key, 0, message, private_key, auth_path)


def test_merkle_signature_invalid_index():
    mss = MerkleSignatureScheme(height=4)
    with pytest.raises(ValueError):
        mss.sign(100, b"message")
