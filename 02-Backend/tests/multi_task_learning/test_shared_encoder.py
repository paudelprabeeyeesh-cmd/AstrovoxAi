from multi_task_learning.shared_encoder import SharedEncoder


def test_shared_encoder_output_shape():
    encoder = SharedEncoder(input_dim=4, shared_dim=8, seed=123)
    x = [0.1, -0.2, 0.3, 0.4]
    h = encoder.forward(x)
    assert len(h) == 8


def test_shared_encoder_deterministic_with_seed():
    encoder1 = SharedEncoder(input_dim=4, shared_dim=8, seed=7)
    encoder2 = SharedEncoder(input_dim=4, shared_dim=8, seed=7)
    x = [0.1, -0.2, 0.3, 0.4]
    assert encoder1.forward(x) == encoder2.forward(x)


def test_shared_encoder_different_seed():
    encoder1 = SharedEncoder(input_dim=4, shared_dim=8, seed=1)
    encoder2 = SharedEncoder(input_dim=4, shared_dim=8, seed=2)
    x = [0.0, 0.0, 0.0, 0.0]
    h1 = encoder1.forward(x)
    h2 = encoder2.forward(x)
    assert h1 != h2


def test_shared_encoder_relu():
    encoder = SharedEncoder(input_dim=2, shared_dim=3, seed=0)
    x = [-10.0, -10.0]
    h = encoder.forward(x)
    assert all(v >= 0.0 for v in h)


def test_shared_encoder_get_parameters():
    encoder = SharedEncoder(input_dim=3, shared_dim=5, seed=0)
    params = encoder.get_parameters()
    assert len(params) == 3
    assert len(params[0]) == 5
