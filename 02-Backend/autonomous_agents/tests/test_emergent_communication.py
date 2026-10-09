import numpy as np
from ..emergent_communication import EmergentCommunication


class TestEmergentCommunication:
    def test_send_and_receive(self):
        ec = EmergentCommunication(vocab_size=32, signal_dim=4)
        content = np.array([0.1, 0.2, 0.3, 0.4])
        signal = ec.send("a1", "a2", content, "greeting")
        result = ec.receive(signal)
        assert result["sender"] == "a1"
        assert result["original_meaning"] == "greeting"

    def test_language_emergence_metric(self):
        ec = EmergentCommunication(vocab_size=16, signal_dim=4)
        content = np.array([0.5, 0.5, 0.5, 0.5])
        signal = ec.send("a", "b", content, "alert")
        ec.receive(signal)
        metric = ec.language_emergence_metric()
        assert 0.0 <= metric <= 1.0

    def test_negotiate_protocol(self):
        ec = EmergentCommunication()
        protocol = ec.negotiate_protocol("a", "b", ["task1", "task2"])
        assert len(protocol) == 2
        assert "task1" in protocol

    def test_vocabulary_growth(self):
        ec = EmergentCommunication(vocab_size=10, signal_dim=2)
        for i in range(5):
            content = np.array([float(i) / 10.0, 0.0])
            ec.send("a", "b", content, f"meaning_{i}")
        assert len(ec.vocabulary) == 5

    def test_signal_stats(self):
        ec = EmergentCommunication()
        content = np.array([0.1, 0.2])
        ec.send("x", "y", content, "m1")
        stats = ec.communication_stats
        assert "x->y" in stats
        assert stats["x->y"] == 1.0
