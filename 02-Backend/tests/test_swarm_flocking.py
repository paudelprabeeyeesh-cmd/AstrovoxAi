import numpy as np
from swarm_intelligence.flocking import Boid, FlockingSimulation


class TestBoid:
    def test_position_clamp(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([1.0, 0.0]))
        boid.edges(10.0, 10.0)
        assert 0.0 <= boid.position[0] <= 10.0
        assert 0.0 <= boid.position[1] <= 10.0

    def test_update_moves_boid(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([0.0, 0.0]))
        boid.update(np.array([1.0, 0.0]), dt=1.0)
        assert np.linalg.norm(boid.velocity) > 0

    def test_speed_limit(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([100.0, 0.0]), max_speed=4.0)
        boid.update(np.array([0.0, 0.0]), dt=1.0)
        assert np.linalg.norm(boid.velocity) <= boid.max_speed + 1e-6

    def test_flock_returns_acceleration(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([1.0, 0.0]))
        accel = boid.flock([], weights=(1.0, 1.0, 1.0))
        assert accel.shape == (2,)

    def test_cohesion_empty(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([1.0, 0.0]))
        coh = boid._cohesion([])
        assert np.allclose(coh, np.zeros(2))

    def test_separation_empty(self):
        boid = Boid(position=np.array([0.0, 0.0]), velocity=np.array([1.0, 0.0]))
        sep = boid._separation([])
        assert np.allclose(sep, np.zeros(2))


class TestFlockingSimulation:
    def test_positions_shape(self):
        sim = FlockingSimulation(5, 20.0, 20.0, seed=42)
        assert sim.positions().shape == (5, 2)

    def test_step_changes_positions(self):
        sim = FlockingSimulation(5, 20.0, 20.0, seed=42)
        before = sim.positions().copy()
        sim.step(dt=1.0)
        after = sim.positions().copy()
        assert not np.allclose(before, after)

    def test_velocities_shape(self):
        sim = FlockingSimulation(5, 20.0, 20.0, seed=42)
        assert sim.velocities().shape == (5, 2)
