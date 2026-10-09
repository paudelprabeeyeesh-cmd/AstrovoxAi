import numpy as np
import pytest
from ..snapshot_versioning import SnapshotVersioning, ModelSnapshot


class TestSnapshotVersioning:
    def test_create_snapshot(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0, 2.0, 3.0]), "layer2": np.array([4.0, 5.0])}
        snapshot = sv.create_snapshot("v1", state, metadata={"task": "mnist"})

        assert snapshot.snapshot_id == "v1"
        assert np.array_equal(snapshot.model_state["layer1"], np.array([1.0, 2.0, 3.0]))
        assert snapshot.metadata["task"] == "mnist"
        assert "v1" in sv.version_history

    def test_duplicate_snapshot_raises(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)

        with pytest.raises(ValueError, match="already exists"):
            sv.create_snapshot("v1", state)

    def test_get_snapshot(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0, 2.0])}
        sv.create_snapshot("v1", state)

        snap = sv.get_snapshot("v1")
        assert snap.snapshot_id == "v1"
        assert np.array_equal(snap.model_state["layer1"], np.array([1.0, 2.0]))

    def test_get_snapshot_not_found(self):
        sv = SnapshotVersioning()
        with pytest.raises(KeyError, match="not found"):
            sv.get_snapshot("nonexistent")

    def test_verify_snapshot(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        sv.create_snapshot("v1", state)
        assert sv.verify_snapshot("v1") is True

    def test_ancestry_with_parent(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0])}
        state2 = {"layer1": np.array([2.0])}
        state3 = {"layer1": np.array([3.0])}

        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2, parent_snapshot_id="v1")
        sv.create_snapshot("v3", state3, parent_snapshot_id="v2")

        ancestry = sv.get_ancestry("v3")
        assert ancestry == ["v3", "v2", "v1"]

    def test_ancestry_without_parent(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)

        ancestry = sv.get_ancestry("v1")
        assert ancestry == ["v1"]

    def test_compare_snapshots(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0, 2.0]), "layer2": np.array([3.0])}
        state2 = {"layer1": np.array([1.5, 2.5]), "layer3": np.array([4.0])}

        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2)

        comparison = sv.compare_snapshots("v1", "v2")

        assert comparison["snapshot_a"] == "v1"
        assert comparison["snapshot_b"] == "v2"
        assert "layer1" in comparison["layer_diffs"]
        assert "layer2" in comparison["layer_diffs"]
        assert "layer3" in comparison["layer_diffs"]

        layer1_diff = comparison["layer_diffs"]["layer1"]
        assert "max_diff" in layer1_diff
        assert "mean_diff" in layer1_diff
        assert "l2_norm" in layer1_diff
        assert np.isclose(layer1_diff["max_diff"], 0.5)
        assert np.isclose(layer1_diff["mean_diff"], 0.5)
        assert np.isclose(layer1_diff["l2_norm"], np.sqrt(0.5))

    def test_hash_consistency(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        snapshot1 = sv.create_snapshot("v1", state)
        snapshot2 = ModelSnapshot(
            snapshot_id="v2",
            model_state={"layer1": np.array([1.0, 2.0, 3.0])},
            metadata={},
            created_at="2024-01-01T00:00:00"
        )
        assert snapshot1.compute_hash() == snapshot2.compute_hash()

    def test_serialization(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0, 2.0]), "layer2": np.array([3.0, 4.0])}
        snapshot = sv.create_snapshot("v1", state, metadata={"task": "test"})
        snapshot_dict = snapshot.to_dict()

        assert "snapshot_id" in snapshot_dict
        assert "model_state" in snapshot_dict
        assert "hash" in snapshot_dict
        assert snapshot_dict["snapshot_id"] == "v1"
        assert isinstance(snapshot_dict["model_state"]["layer1"], list)
