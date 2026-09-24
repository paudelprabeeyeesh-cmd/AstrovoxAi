import numpy as np
from swarm_intelligence.bird_flocking import VFormationFlocking


class TestVFormationFlocking:
    def test_quality_in_range(self):
        flock = VFormationFlocking(5, seed=42)
        flock.step(dt=1.0)
        q = flock.formation_quality()
        assert 0.0 <= q <= 1.0

    def test_leader_rotation(self):
        flock = VFormationFlocking(5, seed=42)
        original_leader = flock.leader_idx
        flock.rotate_leader()
        assert flock.leader_idx != original_leader or len(flock.birds) == 1

    def test_step_changes_positions(self):
        flock = VFormationFlocking(5, seed=42)
        before = np.vstack([b.position for b in flock.birds]).copy()
        flock.step(dt=1.0)
        after = np.vstack([b.position for b in flock.birds]).copy()
        assert not np.allclose(before, after)
