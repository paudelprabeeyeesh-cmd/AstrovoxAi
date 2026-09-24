import unittest

from world_model.physics_engine import PhysicsBody, PhysicsConstraint, PhysicsEngine


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


class TestPhysicsEngine(unittest.TestCase):
    def test_add_body(self):
        engine = PhysicsEngine()
        body = PhysicsBody(id="b1")
        engine.add_body(body)
        self.assertIn("b1", engine.bodies)

    def test_step_moves_body(self):
        engine = PhysicsEngine(gravity=[0.0, -1.0, 0.0], dt=0.016)
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0], velocity=[0.0, 0.0, 0.0])
        engine.add_body(body)
        engine.step()
        self.assertLess(body.position[1], 0.0)

    def test_fixed_body_does_not_move(self):
        engine = PhysicsEngine(gravity=[0.0, -1.0, 0.0], dt=0.016)
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0], fixed=True)
        engine.add_body(body)
        engine.step()
        self.assertEqual(body.position, [0.0, 0.0, 0.0])

    def test_kinetic_energy(self):
        engine = PhysicsEngine()
        body = PhysicsBody(id="b1", mass=2.0, velocity=[1.0, 0.0, 0.0])
        engine.add_body(body)
        energy = engine.kinetic_energy()
        self.assertAlmostEqual(energy, 1.0)

    def test_predict_trajectory(self):
        engine = PhysicsEngine()
        body = PhysicsBody(id="b1", position=[0.0, 0.0, 0.0])
        engine.add_body(body)
        trajectories = engine.predict_trajectory(steps=3)
        self.assertIn("b1", trajectories)
        self.assertEqual(len(trajectories["b1"]), 3)

    def test_constraint_influences_acceleration(self):
        engine = PhysicsEngine(gravity=[0.0, 0.0, 0.0], dt=0.016)
        body_a = PhysicsBody(id="a", position=[0.0, 0.0, 0.0])
        body_b = PhysicsBody(id="b", position=[2.0, 0.0, 0.0])
        engine.add_body(body_a)
        engine.add_body(body_b)
        engine.add_constraint(PhysicsConstraint(body_a="a", body_b="b", rest_length=1.0, stiffness=100.0))
        engine.step()
        self.assertNotAlmostEqual(body_a.velocity[0], 0.0)


if __name__ == "__main__":
    unittest.main()
