# Robotics Integration

AstrovoxAI provides robotics integration with ROS2, sensor fusion, simulation, and manipulation capabilities.

## Features
- **Robot Controller**: Differential drive, trajectory planning, velocity control
- **ROS2 Bridge**: Publish/subscribe to ROS2 topics
- **Sensor Fusion**: Kalman filter for multi-sensor fusion (LiDAR, camera, IMU)
- **Simulation**: Gazebo and Isaac Sim integration
- **Manipulation**: Grasp planning and inverse kinematics

## Usage
```python
from ASTROVOX_AI.ai_core.robotics import RobotController, ROS2Bridge, SensorFusion

controller = RobotController(robot_type='diff_drive')
velocity = controller.compute_velocity(target_x=1.0, target_y=1.0)
pose = controller.update_pose(*velocity, dt=0.1)

ros2 = ROS2Bridge(node_name='astrovox_robot')
ros2.publish_cmd_vel(linear=0.5, angular=0.0)

fusion = SensorFusion()
fusion.add_sensor('lidar', state_dim=3, obs_dim=2)
fusion.add_sensor('camera', state_dim=3, obs_dim=2)
fused = fusion.fuse('lidar', measurement)
```

## Simulation
```python
from ASTROVOX_AI.ai_core.robotics import SimulationBridge

sim = SimulationBridge(simulator='isaac_sim')
sim.spawn_robot('robot.urdf', position=(0, 0, 0))
obs, reward, done, info = sim.step(action)
obs = sim.reset()
```

## Manipulation
```python
from ASTROVOX_AI.ai_core.robotics import GraspPlanner, InverseKinematics

planner = GraspPlanner(num_grasp_candidates=100)
grasps = planner.plan(point_cloud)
best_grasp = planner.select_best_grasp(grasps)

ik = InverseKinematics(num_joints=6)
angles = ik.solve(target_pose)
```
