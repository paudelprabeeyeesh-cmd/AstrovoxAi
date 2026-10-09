from quantum_optimization.qaoa import qaoa_layer


def test_qaoa_layer_shape():
    n = 2
    cost_mat = [[1.0, 0.5], [0.5, 1.0]]
    mixer_mat = [[1.0, 0, 0, 0], [0, -1.0, 0, 0], [0, 0, -1.0, 0], [0, 0, 0, -1.0]]
    params = [0.1, 0.2, 0.3, 0.4]
    probs = qaoa_layer(params, cost_mat, mixer_mat, depth=2)
    assert len(probs) == 2 ** n
    assert abs(sum(probs) - 1.0) < 1e-6
    assert all(0.0 <= p <= 1.0 for p in probs)
