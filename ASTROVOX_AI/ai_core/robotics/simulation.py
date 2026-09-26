from typing import Dict, Any, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SimulationBridge:
    def __init__(self, simulator: str = 'isaac_sim'):
        self.simulator = simulator
        self.available = self._check_simulator()

    def _check_simulator(self) -> bool:
        if self.simulator == 'isaac_sim':
            try:
                import omni.isaac
                return True
            except ImportError:
                logger.warning("Isaac Sim not installed")
                return False
        elif self.simulator == 'gazebo':
            try:
                import ign_tools
                return True
            except ImportError:
                logger.warning("Gazebo not installed")
                return False
        return False

    def spawn_robot(self, robot_urdf: str, position: Tuple[float, float, float]) -> bool:
        if not self.available:
            logger.warning("Simulator unavailable; spawn skipped")
            return False
        logger.info("Spawning robot from %s at %s", robot_urdf, position)
        return True

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        if not self.available:
            obs = np.zeros(10)
            return obs, 0.0, False, {}
        logger.info("Stepping simulation with action %s", action.tolist())
        obs = np.random.randn(10)
        reward = 0.0
        done = False
        return obs, reward, done, {}

    def reset(self) -> np.ndarray:
        if not self.available:
            return np.zeros(10)
        logger.info("Resetting simulation")
        return np.zeros(10)
