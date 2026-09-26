from typing import Dict, Any, List
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RobotController:
    def __init__(self, robot_type: str = 'diff_drive', max_linear_vel: float = 1.0, max_angular_vel: float = 1.0):
        self.robot_type = robot_type
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.state: Dict[str, Any] = {'x': 0.0, 'y': 0.0, 'theta': 0.0}

    def compute_velocity(self, target_x: float, target_y: float) -> tuple[float, float]:
        dx = target_x - self.state['x']
        dy = target_y - self.state['y']
        distance = np.hypot(dx, dy)
        angle = np.arctan2(dy, dx) - self.state['theta']
        linear = min(distance, self.max_linear_vel)
        angular = np.clip(angle, -self.max_angular_vel, self.max_angular_vel)
        return float(linear), float(angular)

    def update_pose(self, linear: float, angular: float, dt: float) -> Dict[str, float]:
        self.state['x'] += linear * np.cos(self.state['theta']) * dt
        self.state['y'] += linear * np.sin(self.state['theta']) * dt
        self.state['theta'] += angular * dt
        return self.state

    def plan_trajectory(self, waypoints: List[tuple[float, float]]) -> List[Dict[str, float]]:
        trajectory = []
        for wx, wy in waypoints:
            v, w = self.compute_velocity(wx, wy)
            trajectory.append({'target_x': wx, 'target_y': wy, 'linear_vel': v, 'angular_vel': w})
        return trajectory


class ROS2Bridge:
    def __init__(self, node_name: str = 'astrovox_robot'):
        self.node_name = node_name
        self.available = self._check_ros2()

    def _check_ros2(self) -> bool:
        try:
            import rclpy
            return True
        except ImportError:
            logger.warning("rclpy not installed; ROS2 bridge unavailable")
            return False

    def publish_cmd_vel(self, linear: float, angular: float) -> None:
        if not self.available:
            return
        import rclpy
        from geometry_msgs.msg import Twist
        node = rclpy.create_node(self.node_name)
        publisher = node.create_publisher(Twist, '/cmd_vel', 10)
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        publisher.publish(msg)
