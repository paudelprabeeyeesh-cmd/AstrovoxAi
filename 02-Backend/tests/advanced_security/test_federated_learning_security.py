from advanced_security.federated_learning_security import (
    FederatedLossyCompression,
    GradientMasker,
    SecureAggregator,
)


def test_secure_aggregator() -> None:
    sa = SecureAggregator()
    payload = {"gradients": [1.0, 2.0, 3.0]}
    masked = sa.mask(payload)
    assert isinstance(masked, bytes)


def test_secure_aggregator_verify() -> None:
    sa = SecureAggregator()
    payload = {"gradients": [1.0, 2.0, 3.0]}
    masked = sa.mask(payload)
    ok, decoded = sa.verify(masked)
    assert ok is True
    assert decoded == payload


def test_gradient_masker() -> None:
    gm = GradientMasker()
    grad = [1.0, 2.0, 3.0, 4.0]
    masked, nonce = gm.mask_gradient(grad)
    assert len(masked) == len(grad)


def test_gradient_masker_recover() -> None:
    gm = GradientMasker()
    grad = [1.0, 2.0, 3.0, 4.0]
    masked, nonce = gm.mask_gradient(grad)
    recovered = gm.unmask_gradient(masked, nonce)
    for r, g in zip(recovered, grad):
        assert abs(r - g) < 1e-6


def test_federated_lossy_compression_topk() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    topk, missed = FederatedLossyCompression.topk(values, 3)
    assert len(topk) == 3
    assert missed == len(values) - 3


def test_federated_lossy_compression_reconstruct() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    topk, _ = FederatedLossyCompression.topk(values, 3)
    reconstructed = FederatedLossyCompression.reconstruct(topk, len(values))
    assert len(reconstructed) == len(values)
    for i, v in topk:
        assert abs(reconstructed[i] - v) < 1e-6
    for i in range(len(values)):
        if i not in {iv[0] for iv in topk}:
            assert reconstructed[i] == 0.0
