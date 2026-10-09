import hashlib

from advanced_security.secure_enclave import Attestation, SealedBlob, SecureEnclave


def test_enclave_id() -> None:
    enclave = SecureEnclave()
    assert len(enclave.enclave_id) == 16
    custom = SecureEnclave(enclave_id="abc123")
    assert custom.enclave_id == "abc123"


def test_extend_measurement() -> None:
    enclave = SecureEnclave()
    enclave.extend_measurement("component", b"data")
    assert "component" in enclave._measurements


def test_attestation() -> None:
    enclave = SecureEnclave()
    att = enclave.attest()
    assert att.enclave_id == enclave.enclave_id
    assert len(att.public_key) == 32
    assert att.timestamp > 0


def test_seal_and_unseal() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext", "ad")
    assert blob.enclave_id == enclave.enclave_id
    result = enclave.unseal(blob, "ad")
    assert isinstance(result, str)


def test_unseal_wrong_enclave_raises() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext")
    wrong = SecureEnclave(enclave_id="other")
    try:
        wrong.unseal(blob)
        assert False
    except ValueError:
        pass


def test_memory_guard() -> None:
    enclave = SecureEnclave()
    assert enclave.memory_guard(0, 16, 65536) is True
    assert enclave.memory_guard(0, 0, 65536) is False
    assert enclave.memory_guard(1000, 70000, 65536) is False
    assert enclave.memory_guard(-1, 16, 65536) is False


def test_sealed_blob_fields() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext", "ad")
    assert isinstance(blob.ciphertext, str)
    assert isinstance(blob.tag, str)
    assert isinstance(blob.nonce, str)
    assert blob.enclave_id == enclave.enclave_id


def test_seal_with_associated_data() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext", "ad")
    result = enclave.unseal(blob, "ad")
    assert result == "plaintext"


def test_unseal_wrong_associated_data_raises() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext", "ad")
    try:
        enclave.unseal(blob, "wrong")
        assert False
    except ValueError:
        pass


def test_unseal_tampered_blob_raises() -> None:
    enclave = SecureEnclave()
    blob = enclave.seal("plaintext")
    blob = SealedBlob(ciphertext=blob.ciphertext, tag="x" * 16, nonce=blob.nonce, enclave_id=blob.enclave_id)
    try:
        enclave.unseal(blob)
        assert False
    except ValueError:
        pass


def test_attestation_includes_measurements() -> None:
    enclave = SecureEnclave()
    enclave.extend_measurement("component", b"data")
    att = enclave.attest()
    assert "component" in att.measurements
    assert att.measurements["component"] == hashlib.sha256(b"data").hexdigest()


def test_default_enclave_id_length() -> None:
    enclave = SecureEnclave()
    assert len(enclave.enclave_id) == 16


def test_sealed_blobs_tracked() -> None:
    enclave = SecureEnclave()
    enclave.seal("first")
    enclave.seal("second")
    assert len(enclave._sealed) == 2
