# Robotics Integration

AstrovoxAI provides robotics integration with ROS2, sensor fusion, simulation, and manipulation capabilities. Enable intelligent robots that can understand, plan, and execute complex tasks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ROBOTICS INTEGRATION STACK                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   AstrovoxAI │    │   ROS2       │    │   Simulation         │  │
│  │   Brain      │◄──►│   Bridge     │◄──►│   Bridge             │  │
│  └──────┬───────┘    └──────────────┘    └──────────┬───────────┘  │
│         │                                            │               │
│  ┌──────▼────────────────────────────────────────────▼───────────┐  │
│  │                    Robot Controller                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │  Kinematics  │  │  Trajectory  │  │  Grasp Planning      │  │  │
│  │  │  Solver      │  │  Planner     │  │  & IK                │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Sensor     │    │   Sensor     │    │   Sensor             │  │
│  │   Fusion     │    │   Processing │    │   Calibration        │  │
│  │   (Kalman)   │    │   Pipeline   │    │   & Mapping          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Robot Controller**: Differential drive, trajectory planning, velocity control
- **ROS2 Bridge**: Publish/subscribe to ROS2 topics with type support
- **Sensor Fusion**: Kalman filter for multi-sensor fusion (LiDAR, camera, IMU)
- **Simulation**: Gazebo and Isaac Sim integration
- **Manipulation**: Grasp planning and inverse kinematics
- **Navigation**: SLAM, path planning, obstacle avoidance
- **Vision**: Object detection, pose estimation, scene understanding

## Robot Controller

```python
from ASTROVOX_AI.ai_core.robotics.robot_controller import RobotController

# Differential drive robot
controller = RobotController(robot_type='diff_drive')

# Compute velocity to target
velocity = controller.compute_velocity(
    target_x=1.0,
    target_y=1.0,
    current_pose=(0.0, 0.0, 0.0)
)

# Update pose
pose = controller.update_pose(*velocity, dt=0.1)

# Generate trajectory
trajectory = controller.plan_trajectory(
    start=(0.0, 0.0),
    goal=(5.0, 3.0),
    waypoints=[(2.0, 1.0), (4.0, 2.0)]
)
```

### Supported Robot Types

| Type | Description |
|------|-------------|
| `diff_drive` | Differential drive (TurtleBot, etc.) |
| `ackermann` | Car-like steering |
| `omnidirectional` | Omni-wheel robots |
| `serial_arm` | Robotic manipulator arms |
| `quadrotor` | Drones and aerial vehicles |
| `legged` | Bipedal/quadruped robots |

## ROS2 Bridge

```python
from ASTROVOX_AI.ai_core.robotics.ros2_bridge import ROS2Bridge

ros2 = ROS2Bridge(node_name='astrovox_robot')

# Publish to ROS2 topics
ros2.publish_cmd_vel(linear=0.5, angular=0.0)
ros2.publish_joint_state(joint_positions=[0.1, -0.5, 0.3])
ros2.publish_twist(twist=[0.5, 0.0, 0.0, 0.0, 0.0, 0.1])

# Subscribe to ROS2 topics
def lidar_callback(msg):
    print(f"LiDAR scan: {msg.ranges}")

ros2.subscribe('/scan', lidar_callback)

# Service calls
result = ros2.call_service(
    '/global_localization',
    service_type='Trigger',
    request={}
)
```

### ROS2 Topics

| Topic | Type | Direction |
|-------|------|-----------|
| `/cmd_vel` | `geometry_msgs/Twist` | Publish |
| `/odom` | `nav_msgs/Odometry` | Subscribe |
| `/scan` | `sensor_msgs/LaserScan` | Subscribe |
| `/joint_states` | `sensor_msgs/JointState` | Publish |
| `/map` | `nav_msgs/OccupancyGrid` | Subscribe |
| `/tf` | `tf2_msgs/TFMessage` | Subscribe |

## Sensor Fusion

```python
from ASTROVOX_AI.ai_core.robotics.sensor_fusion import SensorFusion

fusion = SensorFusion()

# Register sensors
fusion.add_sensor('lidar', state_dim=3, obs_dim=2)
fusion.add_sensor('camera', state_dim=3, obs_dim=2)
fusion.add_sensor('imu', state_dim=3, obs_dim=6)

# Fuse measurements
fused_state = fusion.fuse(
    'lidar',
    measurement=lidar_scan,
    timestamp=time.time()
)

fused_state = fusion.fuse(
    'camera',
    measurement=image_features,
    timestamp=time.time()
)

# Get estimated state
position, covariance = fusion.get_state()
```

### Supported Sensors

| Sensor | State Dim | Observation Dim |
|--------|-----------|-----------------|
| LiDAR | 3 | 2 |
| Camera | 3 | 2 |
| IMU | 3 | 6 |
| GPS | 3 | 3 |
| Wheel Encoder | 3 | 2 |
| Force/Torque | 6 | 6 |

## Simulation

### Gazebo Integration

```python
from ASTROVOX_AI.ai_core.robotics.simulation import SimulationBridge

sim = SimulationBridge(simulator='gazebo')

# Spawn robot
sim.spawn_robot(
    sdf='robot.sdf',
    position=(0.0, 0.0, 0.0),
    orientation=(0.0, 0.0, 0.0)
)

# Step simulation
obs, reward, done, info = sim.step(action)

# Reset simulation
obs = sim.reset()
```

### Isaac Sim Integration

```python
from ASTROVOX_AI.ai_core.robotics.isaac_sim_bridge import IsaacSimBridge

sim = IsaacSimBridge(
    scene='warehouse.usd',
    robot='franka_panda.usd'
)

# Physics stepping with reinforcement learning
for step in range(num_steps):
    obs = sim.get_observations()
    action = policy(obs)
    sim.apply_action(action)
    sim.step()
    reward = sim.get_reward()
```

## Manipulation

### Grasp Planning

```python
from ASTROVOX_AI.ai_core.robotics.grasp_planner import GraspPlanner

planner = GraspPlanner(
    num_grasp_candidates=100,
    gripper_width=0.08,
    finger_depth=0.04
)

# Plan grasps for a point cloud
grasps = planner.plan(point_cloud=scene_pcd)

# Select best grasp
best_grasp = planner.select_best_grasp(grasps, metric='grasp_quality')

# Execute grasp
execution_result = robot.execute_grasp(best_grasp)
```

### Inverse Kinematics

```python
from ASTROVOX_AI.ai_core.robotics.inverse_kinematics import InverseKinematics

ik = InverseKinematics(
    num_joints=6,
    joint_limits=[(-180, 180)] * 6,
    base_frame='base_link',
    end_effector_frame='tool0'
)

# Solve IK for target pose
angles = ik.solve(
    target_pose=(0.5, 0.3, 0.8, 0.0, 1.57, 0.0)  # x, y, z, roll, pitch, yaw
)

# Multiple solutions
solutions = ik.solve_multiple(
    target_pose=target_pose,
    num_solutions=5
)
```

## Navigation

```python
from ASTROVOX_AI.ai_core.robotics.navigation import Navigator

nav = Navigator(map_file='warehouse_map.yaml')

# Plan path
path = nav.plan_path(
    start=(0.0, 0.0),
    goal=(5.0, 3.0),
    algorithm='astar'  # or 'rrt', 'rrt_star'
)

# Follow path
for waypoint in path:
    velocity = nav.compute_velocity(waypoint, current_pose)
    robot.set_velocity(velocity)

# Local planning with obstacle avoidance
local_plan = nav.local_plan(
    global_path=path,
    obstacles=detected_obstacles,
    robot_radius=0.3
)
```

## Vision Integration

```python
from ASTROVOX_AI.ai_core.robotics.vision import RobotVision

vision = RobotVision(
    camera_intrinsics=intrinsics,
    camera_extrinsics=extrinsics
)

# Object detection
detections = vision.detect_objects(rgb_image)

# Pose estimation
pose = vision.estimate_pose(
    object_model='mug.stl',
    rgb_image=image,
    depth_image=depth
)

# Semantic segmentation
segments = vision.segment_scene(rgb_image)
```

## Safety Considerations

- Emergency stop handling
- Collision avoidance
- Workspace limits enforcement
- Velocity and acceleration limits
- Force/torque sensing for contact detection
