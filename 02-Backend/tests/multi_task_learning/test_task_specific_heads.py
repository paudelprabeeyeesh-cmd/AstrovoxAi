from multi_task_learning.task_specific_heads import TaskSpecificHead


def test_task_specific_head_output_shape():
    head = TaskSpecificHead(shared_dim=8, output_dim=3, seed=1)
    h = [0.1, -0.2, 0.3, 0.4, 0.5, -0.1, 0.2, 0.0]
    out = head.forward(h)
    assert len(out) == 3


def test_task_specific_head_different_seeds():
    head1 = TaskSpecificHead(shared_dim=4, output_dim=2, seed=1)
    head2 = TaskSpecificHead(shared_dim=4, output_dim=2, seed=2)
    h = [0.1, 0.2, 0.3, 0.4]
    out1 = head1.forward(h)
    out2 = head2.forward(h)
    assert out1 != out2


def test_task_specific_head_same_seed():
    head1 = TaskSpecificHead(shared_dim=4, output_dim=2, seed=5)
    head2 = TaskSpecificHead(shared_dim=4, output_dim=2, seed=5)
    h = [0.1, 0.2, 0.3, 0.4]
    assert head1.forward(h) == head2.forward(h)


def test_task_specific_head_parameters():
    head = TaskSpecificHead(shared_dim=4, output_dim=2, seed=0)
    params = head.get_parameters()
    assert "weights" in params
    assert "bias" in params
    assert len(params["weights"]) == 4
    assert len(params["weights"][0]) == 2
    assert len(params["bias"]) == 2
