import os
import sys

from fastapi import FastAPI

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import torch
import torch.nn as nn
from models.llm.debugger.inspector import ActivationInfo, ActivationViewer, GradientInfo, GradientInspector, TokenInfo, TokenInspector, WeightInfo, WeightInspector
from models.llm.debugger.profiler import ComputeProfiler, ComputeSnapshot, MemoryProfiler, MemorySnapshot, TokenProbabilityEntry, TokenProbabilityTracker
from models.llm.debugger.server import DebugServer, create_debug_app
from models.llm.debugger.visualizer import AttentionMapData, AttentionMapVisualizer, GradientFlowData, GradientFlowVisualizer, HiddenStateData, HiddenStateVisualizer, KVCacheData, KVCacheVisualizer


def make_tiny_model() -> nn.Module:
    return nn.Sequential(nn.Linear(8, 16), nn.ReLU(), nn.Linear(16, 8))


class TestAttentionMapVisualizer:
    def test_capture_returns_data(self):
        viz = AttentionMapVisualizer()
        scores = torch.randn(1, 2, 8, 8)
        data = viz.capture(scores, layer=0, head=0)
        assert isinstance(data, AttentionMapData)
        assert data.layer == 0
        assert data.head == 0
        assert data.sequence_length == 8
        assert data.num_heads == 2
        assert len(data.attention_scores) == 8

    def test_to_dict(self):
        viz = AttentionMapVisualizer()
        scores = torch.randn(1, 2, 4, 4)
        data = viz.capture(scores, layer=0, head=1)
        result = viz.to_dict(data)
        assert result["type"] == "attention_map"
        assert result["layer"] == 0
        assert result["head"] == 1
        assert len(result["attention_scores"]) == 4


class TestKVCacheVisualizer:
    def test_capture_returns_data(self):
        viz = KVCacheVisualizer()
        kv = type("KVC", (), {"max_blocks": 4, "free_blocks": [2, 3], "key_blocks": [None, None], "value_blocks": [None, None]})()
        data = viz.capture(kv, layer=0)
        assert isinstance(data, KVCacheData)
        assert data.layer == 0
        assert data.max_blocks == 4
        assert data.used_blocks == 2

    def test_to_dict(self):
        viz = KVCacheVisualizer()
        kv = type("KVC", (), {"max_blocks": 2, "free_blocks": [0], "key_blocks": [None], "value_blocks": [None]})()
        data = viz.capture(kv, layer=1)
        result = viz.to_dict(data)
        assert result["type"] == "kv_cache"
        assert result["used_blocks"] == 1


class TestHiddenStateVisualizer:
    def test_capture_returns_data(self):
        viz = HiddenStateVisualizer()
        hidden = torch.randn(1, 4, 16)
        data = viz.capture(hidden, layer=0)
        assert isinstance(data, HiddenStateData)
        assert data.layer == 0
        assert data.norm > 0
        assert data.mean > -10 and data.mean < 10

    def test_to_dict(self):
        viz = HiddenStateVisualizer()
        hidden = torch.randn(1, 2, 8)
        data = viz.capture(hidden, layer=1)
        result = viz.to_dict(data)
        assert result["type"] == "hidden_state"
        assert result["norm"] == data.norm


class TestGradientFlowVisualizer:
    def test_capture_returns_data(self):
        viz = GradientFlowVisualizer()
        model = make_tiny_model()
        model.zero_grad()
        x = torch.randn(1, 8)
        out = model(x)
        out.sum().backward()
        data = viz.capture(model, layer=0)
        assert isinstance(data, list)
        assert all(isinstance(d, GradientFlowData) for d in data)

    def test_to_dict(self):
        viz = GradientFlowVisualizer()
        model = make_tiny_model()
        model.zero_grad()
        x = torch.randn(1, 8)
        out = model(x)
        out.sum().backward()
        data = viz.capture(model, layer=0)
        result = viz.to_dict(data)
        assert result["type"] == "gradient_flow"
        assert "values" in result
        assert len(result["values"]) == len(data)


class TestMemoryProfiler:
    def test_snapshot_creation(self):
        profiler = MemoryProfiler()
        profiler.start()
        snap = profiler.take_snapshot(layer_id="test")
        assert isinstance(snap, MemorySnapshot)
        assert snap.layer_id == "test"
        assert snap.allocated_gb >= 0

    def test_summary_empty(self):
        profiler = MemoryProfiler()
        assert profiler.summary() == {}

    def test_summary_with_snapshots(self):
        profiler = MemoryProfiler()
        profiler.start()
        profiler.take_snapshot()
        profiler.take_snapshot()
        s = profiler.summary()
        assert s["snapshots"] == 2
        assert "max_allocated_gb" in s


class TestComputeProfiler:
    def test_profile_layer(self):
        profiler = ComputeProfiler()
        layer = nn.Linear(4, 4)
        x = torch.randn(1, 4)
        snap = profiler.profile_layer(layer, "linear_0", x)
        assert isinstance(snap, ComputeSnapshot)
        assert snap.layer_id == "linear_0"
        assert snap.duration_ms >= 0

    def test_summary_empty(self):
        profiler = ComputeProfiler()
        assert profiler.summary() == {}

    def test_summary_with_snapshots(self):
        profiler = ComputeProfiler()
        for i in range(3):
            layer = nn.Linear(4, 4)
            x = torch.randn(1, 4)
            profiler.profile_layer(layer, f"layer_{i}", x)
        s = profiler.summary()
        assert s["layers"] == 3
        assert s["total_duration_ms"] >= 0


class TestTokenProbabilityTracker:
    def test_log_step(self):
        tracker = TokenProbabilityTracker(top_k=5)
        logits = torch.randn(32)
        tracker.log_step(step=0, logits=logits, token_id=1)
        assert tracker.summary()["steps"] == 1

    def test_history(self):
        tracker = TokenProbabilityTracker(top_k=3)
        for step in range(5):
            logits = torch.randn(16)
            tracker.log_step(step=step, logits=logits, token_id=step % 16)
        h = tracker.history()
        assert len(h) == 5
        assert h[0]["step"] == 0

    def test_summary_empty(self):
        tracker = TokenProbabilityTracker()
        assert tracker.summary() == {}


class TestTokenInspector:
    def test_inspect(self):
        embedding = nn.Embedding(16, 8)
        inspector = TokenInspector(embedding)
        info = inspector.inspect(token_id=3)
        assert isinstance(info, TokenInfo)
        assert info.token_id == 3
        assert info.embedding_norm > 0

    def test_to_dict(self):
        embedding = nn.Embedding(16, 8)
        inspector = TokenInspector(embedding)
        info = inspector.inspect(token_id=1)
        result = inspector.to_dict(info)
        assert result["type"] == "token"
        assert result["token_id"] == 1


class TestActivationViewer:
    def test_register_and_forward(self):
        model = make_tiny_model()
        viewer = ActivationViewer()
        viewer.register_hooks(model)
        viewer.forward(model, torch.zeros(1, 8, dtype=torch.long))
        assert viewer.read(0) is not None
        viewer.close()

    def test_read_returns_info(self):
        model = make_tiny_model()
        viewer = ActivationViewer()
        viewer.register_hooks(model)
        viewer.forward(model, torch.zeros(1, 8, dtype=torch.long))
        info = viewer.read(0)
        assert isinstance(info, ActivationInfo)
        assert info.layer == 0
        viewer.close()

    def test_to_dict(self):
        model = make_tiny_model()
        viewer = ActivationViewer()
        viewer.register_hooks(model)
        viewer.forward(model, torch.zeros(1, 8, dtype=torch.long))
        info = viewer.read(0)
        result = viewer.to_dict(info)
        assert result["type"] == "activation"
        viewer.close()


class TestWeightInspector:
    def test_read(self):
        model = make_tiny_model()
        inspector = WeightInspector()
        info = inspector.read(model, "0.weight")
        assert isinstance(info, WeightInfo)
        assert info.name == "0.weight"
        assert info.trainable is True

    def test_to_dict(self):
        model = make_tiny_model()
        inspector = WeightInspector()
        info = inspector.read(model, "0.weight")
        result = inspector.to_dict(info)
        assert result["type"] == "weight"
        assert result["name"] == "0.weight"


class TestGradientInspector:
    def test_read(self):
        model = make_tiny_model()
        model.zero_grad()
        x = torch.randn(1, 8)
        out = model(x)
        out.sum().backward()
        inspector = GradientInspector()
        info = inspector.read(model, "0.weight")
        assert isinstance(info, GradientInfo)
        assert info.exists is True

    def test_to_dict(self):
        model = make_tiny_model()
        model.zero_grad()
        x = torch.randn(1, 8)
        out = model(x)
        out.sum().backward()
        inspector = GradientInspector()
        info = inspector.read(model, "0.weight")
        result = inspector.to_dict(info)
        assert result["type"] == "gradient"
        assert result["exists"] is True


class TestDebugServer:
    def test_create_app(self):
        model = make_tiny_model()
        app = create_debug_app(model, None)
        assert isinstance(app, FastAPI)

    def test_server_initializes(self):
        model = make_tiny_model()
        server = DebugServer(model, None)
        assert server.app is not None
        assert server.model is model
