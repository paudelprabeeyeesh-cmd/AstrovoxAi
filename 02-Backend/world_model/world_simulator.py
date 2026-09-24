from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PhysicsBody:
    id: str
    mass: float = 1.0
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    acceleration: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    radius: float = 0.5
    fixed: bool = False


@dataclass
class PhysicsConstraint:
    body_a: str
    body_b: str
    rest_length: float = 1.0
    stiffness: float = 1.0


class PhysicsWorld:
    def __init__(self, gravity: List[float] = None, dt: float = 0.016):
        self.gravity = gravity if gravity is not None else [0.0, -9.81, 0.0]
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
            for i in range(3):
                body.acceleration[i] = self.gravity[i]
            for constraint in self.constraints:
                if constraint.body_a == body.id or constraint.body_b == body.id:
                    other_id = constraint.body_b if body.id == constraint.body_a else constraint.body_a
                    other = self.bodies.get(other_id)
                    if other is not None:
                        dx = other.position[0] - body.position[0]
                        dy = other.position[1] - body.position[1]
                        dz = other.position[2] - body.position[2]
                        distance = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
                        if distance > 1e-6:
                            direction = [dx / distance, dy / distance, dz / distance]
                            displacement = distance - constraint.rest_length
                            force = constraint.stiffness * displacement
                            for i in range(3):
                                body.acceleration[i] += force * direction[i] / max(body.mass, 1e-6)
            for i in range(3):
                body.velocity[i] += body.acceleration[i] * self.dt
                body.position[i] += body.velocity[i] * self.dt
        self._resolve_constraints()

    def _resolve_constraints(self, iterations: int = 4) -> None:
        for _ in range(iterations):
            for constraint in self.constraints:
                a = self.bodies.get(constraint.body_a)
                b = self.bodies.get(constraint.body_b)
                if a is None or b is None:
                    continue
                dx = b.position[0] - a.position[0]
                dy = b.position[1] - a.position[1]
                dz = b.position[2] - a.position[2]
                distance = (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5
                if distance < 1e-6:
                    continue
                direction = [dx / distance, dy / distance, dz / distance]
                correction = (distance - constraint.rest_length) * 0.5
                for i in range(3):
                    corr = correction * direction[i]
                    if not a.fixed:
                        a.position[i] += corr
                    if not b.fixed:
                        b.position[i] -= corr

    def kinetic_energy(self) -> float:
        return sum(
            0.5 * b.mass * (b.velocity[0] ** 2 + b.velocity[1] ** 2 + b.velocity[2] ** 2)
            for b in self.bodies.values()
        )

    def predict(self, steps: int = 10) -> Dict[str, List[List[float]]]:
        trajectories: Dict[str, List[List[float]]] = {bid: [] for bid in self.bodies}
        for _ in range(steps):
            self.step()
            for bid, body in self.bodies.items():
                trajectories[bid].append(list(body.position))
        return trajectories


class WorldSimulator:
    def __init__(self):
        self.worlds: Dict[str, PhysicsWorld] = {}
        self.history: Dict[str, List[Dict]] = {}

    def create_world(self, world_id: str, gravity: List[float] = None, dt: float = 0.016) -> PhysicsWorld:
        world = PhysicsWorld(gravity=gravity, dt=dt)
        self.worlds[world_id] = world
        self.history[world_id] = []
        return world

    def step(self, world_id: str) -> Dict[str, List[float]]:
        world = self.worlds[world_id]
        world.step()
        snapshot = {
            bid: {"position": list(b.position), "velocity": list(b.velocity)}
            for bid, b in world.bodies.items()
        }
        self.history[world_id].append(snapshot)
        return {bid: list(b.position) for bid, b in world.bodies.items()}

    def simulate(self, world_id: str, steps: int = 10) -> Dict[str, List[List[float]]]:
        world = self.worlds[world_id]
        return world.predict(steps=steps)
