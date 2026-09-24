import pytest
import numpy as np
from world_model.world_simulator import PhysicsWorld, WorldSimulator, PhysicsBody, PhysicsConstraint


class TestPhysicsWorld:
    def test_step_updates_position(self):
        world = PhysicsWorld(dt=0.1)
        body = PhysicsBody(id="b1", position=np.array([0.0, 0.0, 0.0]), velocity=np.array([1.0, 0.0, 0.0]))
        world.add_body(body)
        world.step()
        assert np.allclose(body.position, np.array([0.1, -0.0981, 0.0]), atol=1e-3)

    def test_fixed_body_does_not_move(self):
        world = PhysicsWorld(dt=0.1)
        body = PhysicsBody(id="b1", position=np.array([0.0, 0.0, 0.0]), velocity=np.array([1.0, 0.0, 0.0]), fixed=True)
        world.add_body(body)
        world.step()
        assert np.allclose(body.position, np.zeros(3))

    def test_constraint_affects_bodies(self):
        world = PhysicsWorld(dt=0.1)
        world.add_body(PhysicsBody(id="a", position=np.array([0.0, 0.0, 0.0])))
        world.add_body(PhysicsBody(id="b", position=np.array([2.0, 0.0, 0.0])))
        world.add_constraint(PhysicsConstraint(body_a="a", body_b="b", rest_length=1.0, stiffness=10.0))
        world.step()
        dist = np.linalg.norm(world.bodies["a"].position - world.bodies["b"].position)
        assert abs(dist - 1.0) < 0.1

    def test_kinetic_energy(self):
        world = PhysicsWorld(dt=0.1)
        world.add_body(PhysicsBody(id="b1", mass=1.0, velocity=np.array([1.0, 0.0, 0.0])))
        assert world.kinetic_energy() == pytest.approx(0.5)

    def test_predict_trajectory(self):
        world = PhysicsWorld(dt=0.1)
        world.add_body(PhysicsBody(id="b1", position=np.array([0.0, 0.0, 0.0]), velocity=np.array([1.0, 0.0, 0.0])))
        traj = world.predict(steps=3)
        assert "b1" in traj
        assert traj["b1"].shape == (3, 3)


class TestWorldSimulator:
    def test_create_and_step_world(self):
        sim = WorldSimulator()
        world = sim.create_world("w1", dt=0.1)
        body = PhysicsBody(id="b1", position=np.array([0.0, 0.0, 0.0]), velocity=np.array([1.0, 0.0, 0.0]))
        world.add_body(body)
        positions = sim.step("w1")
        assert "b1" in positions
        assert np.allclose(positions["b1"], np.array([0.1, -0.0981, 0.0]), atol=1e-3)

    def test_simulate_returns_trajectories(self):
        sim = WorldSimulator()
        world = sim.create_world("w1")
        world.add_body(PhysicsBody(id="b1", position=np.zeros(3), velocity=np.array([1.0, 0.0, 0.0])))
        trajectories = sim.simulate("w1", steps=3)
        assert "b1" in trajectories
        assert trajectories["b1"].shape == (3, 3)

    def test_history_records_snapshots(self):
        sim = WorldSimulator()
        world = sim.create_world("w1", dt=0.1)
        world.add_body(PhysicsBody(id="b1", position=np.zeros(3), velocity=np.array([1.0, 0.0, 0.0])))
        sim.step("w1")
        assert len(sim.history["w1"]) == 1
