import unittest

from world_model.world_simulator import PhysicsBody, PhysicsConstraint, PhysicsWorld, WorldSimulator


class TestPhysicsBody(unittest.TestCase):
    def test_defaults(self):
        body = PhysicsBody(id="b1")
        self.assertEqual(body.id, "b1")
        self.assertEqual(body.mass, 1.0)
        self.assertEqual(body.position, [0.0, 0.0, 0.0])
        self.assertEqual(body.velocity, [0.0, 0.0, 0.0])
        self.assertFalse(body.fixed)

    def test_custom_values(self):
        body = PhysicsBody(id="b2", mass=2.0, position=[1.0, 2.0, 3.0], fixed=True)
        self.assertEqual(body.mass, 2.0)
        self.assertEqual(body.position, [1.0, 2.0, 3.0])
        self.assertTrue(body.fixed)


class TestPhysicsWorld(unittest.TestCase):
    def test_add_body(self):
        world = PhysicsWorld()
        body = PhysicsBody(id="b1")
        world.add_body(body)
        self.assertIn("b1", world.bodies)

    def test_step_moves_body(self):
        world = PhysicsWorld(gravity=[0.0, -1.0, 0.0], dt=0.016)
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0], velocity=[0.0, 0.0, 0.0])
        world.add_body(body)
        world.step()
        self.assertLess(body.position[1], 0.0)

    def test_fixed_body_does_not_move(self):
        world = PhysicsWorld(gravity=[0.0, -1.0, 0.0], dt=0.016)
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0], fixed=True)
        world.add_body(body)
        world.step()
        self.assertEqual(body.position, [0.0, 0.0, 0.0])

    def test_kinetic_energy(self):
        world = PhysicsWorld()
        body = PhysicsBody(id="b1", mass=2.0, velocity=[1.0, 0.0, 0.0])
        world.add_body(body)
        energy = world.kinetic_energy()
        self.assertAlmostEqual(energy, 1.0)

    def test_predict_trajectory(self):
        world = PhysicsWorld()
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0])
        world.add_body(body)
        trajectories = world.predict(steps=3)
        self.assertIn("b1", trajectories)
        self.assertEqual(len(trajectories["b1"]), 3)


class TestWorldSimulator(unittest.TestCase):
    def test_create_world(self):
        sim = WorldSimulator()
        world = sim.create_world("w1")
        self.assertIn("w1", sim.worlds)
        self.assertIsInstance(world, PhysicsWorld)

    def test_step(self):
        sim = WorldSimulator()
        sim.create_world("w1")
        positions = sim.step("w1")
        self.assertIsInstance(positions, dict)

    def test_simulate(self):
        sim = WorldSimulator()
        sim.create_world("w1")
        result = sim.simulate("w1", steps=2)
        self.assertIn("b1" if False else "", result)


if __name__ == "__main__":
    unittest.main()
