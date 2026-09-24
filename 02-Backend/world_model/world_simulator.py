from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np


@dataclass
class PhysicsBody:
    id: str
    mass: float = 1.0
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    radius: float = 0.5
    fixed: bool = False


@dataclass
class PhysicsConstraint:
    body_a: str
    body_b: str
    rest_length: float = 1.0
    stiffness: float = 1.0


class PhysicsWorld:
    def __init__(self, gravity: np.ndarray = None, dt: float = 0.016):
        self.gravity = gravity if gravity is not None else np.array([0.0, -9.81, 0.0])
        self.dt = dt
        self.bodies: Dict[str, PhysicsBody] = {}
        self.constraints: List[PhysicsConstraint] = []

    def add_body(self, body: PhysicsBody) -> None:
        self.bodies[body.id] = body

    def add_constraint(self, constraint: PhysicsConstraint) -> None:
        self.constraints.append(constraint)

    def step(self) -> None:
        for body in self.bodies.values():
            if body.fixed:
                continue
            body.acceleration = self.gravity.copy()
            for constraint in self.constraints:
                if constraint.body_a == body.id or constraint.body_b == body.id:
                    other_id = constraint.body_b if body.id == constraint.body_a else constraint.body_a
                    other = self.bodies.get(other_id)
                    if other is not None:
                        direction = other.position - body.position
                        distance = np.linalg.norm(direction)
                        if distance > 1e-6:
                            direction = direction / distance
                            displacement = distance - constraint.rest_length
                            force = constraint.stiffness * displacement * direction
                            body.acceleration += force / max(body.mass, 1e-6)
            body.velocity += body.acceleration * self.dt
            body.position += body.velocity * self.dt
        self._resolve_constraints()

    def _resolve_constraints(self, iterations: int = 4) -> None:
        for _ in range(iterations):
            for constraint in self.constraints:
                a = self.bodies.get(constraint.body_a)
                b = self.bodies.get(constraint.body_b)
                if a is None or b is None:
                    continue
                direction = b.position - a.position
                distance = np.linalg.norm(direction)
                if distance < 1e-6:
                    continue
                direction = direction / distance
                correction = (distance - constraint.rest_length) * 0.5 * direction
                if not a.fixed:
                    a.position += correction
                if not b.fixed:
                    b.position -= correction

    def kinetic_energy(self) -> float:
        return float(sum(0.5 * b.mass * np.dot(b.velocity, b.velocity) for b in self.bodies.values()))

    def predict(self, steps: int = 10) -> Dict[str, np.ndarray]:
        trajectories: Dict[str, List[np.ndarray]] = {bid: [] for bid in self.bodies}
        for _ in range(steps):
            self.step()
            for bid, body in self.bodies.items():
                trajectories[bid].append(body.position.copy())
        return {bid: np.array(positions) for bid, positions in trajectories.items()}


class WorldSimulator:
    def __init__(self):
        self.worlds: Dict[str, PhysicsWorld] = {}
        self.history: Dict[str, List[Dict]] = {}

    def create_world(self, world_id: str, gravity: np.ndarray = None, dt: float = 0.016) -> PhysicsWorld:
        world = PhysicsWorld(gravity=gravity, dt=dt)
        self.worlds[world_id] = world
        self.history[world_id] = []
        return world

    def step(self, world_id: str) -> Dict[str, np.ndarray]:
        world = self.worlds[world_id]
        world.step()
        snapshot = {bid: {"position": b.position.copy(), "velocity": b.velocity.copy()} for bid, b in world.bodies.items()}
        self.history[world_id].append(snapshot)
        return {bid: b.position.copy() for bid, b in world.bodies.items()}

    def simulate(self, world_id: str, steps: int = 10) -> Dict[str, np.ndarray]:
        world = self.worlds[world_id]
        return world.predict(steps=steps)
