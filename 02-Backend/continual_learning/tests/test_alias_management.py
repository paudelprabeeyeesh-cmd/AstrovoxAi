import numpy as np
import pytest
from ..snapshot_versioning import SnapshotVersioning
from ..alias_management import AliasManagement


class TestAliasManagement:
    def test_create_alias(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")

        assert am.resolve_alias("latest") == "v1"
        assert "latest" in am.list_aliases()

    def test_duplicate_alias_raises(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)
        sv.create_snapshot("v2", state)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")

        with pytest.raises(ValueError, match="already exists"):
            am.create_alias("latest", "v2")

    def test_update_alias(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0])}
        state2 = {"layer1": np.array([2.0])}
        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")
        am.update_alias("latest", "v2")

        assert am.resolve_alias("latest") == "v2"

    def test_update_alias_not_found(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)

        am = AliasManagement(sv)
        with pytest.raises(KeyError, match="not found"):
            am.update_alias("nonexistent", "v1")

    def test_resolve_alias_not_found(self):
        sv = SnapshotVersioning()
        am = AliasManagement(sv)
        with pytest.raises(KeyError, match="not found"):
            am.resolve_alias("nonexistent")

    def test_alias_history(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0])}
        state2 = {"layer1": np.array([2.0])}
        state3 = {"layer1": np.array([3.0])}
        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2)
        sv.create_snapshot("v3", state3)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")
        am.update_alias("latest", "v2")
        am.update_alias("latest", "v3")

        history = am.get_alias_history("latest")
        assert len(history) == 3
        assert history[0]["snapshot_id"] == "v1"
        assert history[1]["snapshot_id"] == "v2"
        assert history[2]["snapshot_id"] == "v3"
        assert "previous_snapshot_id" in history[1]
        assert history[1]["previous_snapshot_id"] == "v1"

    def test_rollback_alias(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0])}
        state2 = {"layer1": np.array([2.0])}
        state3 = {"layer1": np.array([3.0])}
        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2)
        sv.create_snapshot("v3", state3)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")
        am.update_alias("latest", "v2")
        am.update_alias("latest", "v3")

        result = am.rollback_alias("latest", steps=1)
        assert result == "v2"
        assert am.resolve_alias("latest") == "v2"

    def test_rollback_alias_invalid_steps(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")

        with pytest.raises(ValueError, match="Cannot rollback"):
            am.rollback_alias("latest", steps=1)

    def test_backward_compatible_snapshot(self):
        sv = SnapshotVersioning()
        state1 = {"layer1": np.array([1.0])}
        state2 = {"layer1": np.array([2.0])}
        sv.create_snapshot("v1", state1)
        sv.create_snapshot("v2", state2)

        am = AliasManagement(sv)
        am.create_alias("latest", "v2")

        compatibility_matrix = {"v2": ["v1"]}
        compatible = am.get_backward_compatible_snapshot("latest", compatibility_matrix)
        assert compatible == "v1"

    def test_list_aliases(self):
        sv = SnapshotVersioning()
        state = {"layer1": np.array([1.0])}
        sv.create_snapshot("v1", state)
        sv.create_snapshot("v2", state)

        am = AliasManagement(sv)
        am.create_alias("latest", "v1")
        am.create_alias("stable", "v2")

        aliases = am.list_aliases()
        assert len(aliases) == 2
        assert aliases["latest"] == "v1"
        assert aliases["stable"] == "v2"
