from model_architecture.feedforward import FeedForward


class TestFeedForward:
    def test_output_shape(self):
        B, T, C = 2, 5, 32
        model = FeedForward(d_model=C)
        x = [[[0.1 for _ in range(C)] for _ in range(T)] for _ in range(B)]
        out = model.forward(x)
        assert len(out) == B
        assert len(out[0]) == T
        assert len(out[0][0]) == C
