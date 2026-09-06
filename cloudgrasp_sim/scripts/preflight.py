#!/usr/bin/python3
"""Bounded, read-only readiness check using wall time, including paused simulation."""
import argparse
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from controller_manager_msgs.srv import ListControllers
from grasping_msgs.action import FindGraspableObjects
from moveit_msgs.action import MoveGroup
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import JointState, PointCloud2

parser = argparse.ArgumentParser()
parser.add_argument('--timeout', type=float, default=15)
args = parser.parse_args()
rclpy.init()
node = rclpy.create_node('cloudgrasp_preflight')
seen = {'clock': [], 'joints': set(), 'joint_time': 0., 'cloud_time': 0.}
required = {'shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint', 'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint', 'robotiq_85_left_knuckle_joint'}

def clock_cb(msg):
    stamp = msg.clock.sec * 1000000000 + msg.clock.nanosec
    if not seen['clock']:
        seen['clock'] = [stamp, stamp, time.monotonic()]
    elif stamp != seen['clock'][1]:
        seen['clock'][1:] = [stamp, time.monotonic()]

def joints_cb(msg):
    seen['joints'] = set(msg.name)
    seen['joint_time'] = time.monotonic()

def cloud_cb(msg):
    if msg.width * msg.height > 0:
        seen['cloud_time'] = time.monotonic()

node.create_subscription(Clock, '/clock', clock_cb, qos_profile_sensor_data)
node.create_subscription(JointState, '/joint_states', joints_cb, qos_profile_sensor_data)
node.create_subscription(PointCloud2, '/camera/points', cloud_cb, qos_profile_sensor_data)
controllers = node.create_client(ListControllers, '/controller_manager/list_controllers')
move = ActionClient(node, MoveGroup, '/move_action')
find = ActionClient(node, FindGraspableObjects, '/find_objects')
active = set()
pending = None
last_query = 0.
end = time.monotonic() + args.timeout
missing = []
last_report = 0.
try:
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=.1)
        now = time.monotonic()
        if pending is not None and pending.done():
            result = pending.result()
            active = {c.name for c in result.controller if c.state == 'active'} if result else set()
            pending = None
        if pending is not None and now-last_query > 3.:
            controllers.remove_pending_request(pending)
            pending.cancel()
            pending = None
        if pending is None and controllers.service_is_ready() and now-last_query > 1.:
            pending = controllers.call_async(ListControllers.Request())
            last_query = now
        clock = seen['clock']
        checks = {
            'advancing /clock (Gazebo may be paused)': bool(clock) and clock[1] > clock[0] and now-clock[2] < 2.,
            'fresh arm and gripper joint states': required <= seen['joints'] and now-seen['joint_time'] < 2.,
            'fresh camera point cloud': now-seen['cloud_time'] < 3.,
            'active controllers': {'joint_state_broadcaster', 'arm_controller', 'gripper_controller'} <= active,
            'MoveIt action server': move.server_is_ready(),
            'perception action server': find.server_is_ready(),
        }
        missing = [name for name, ok in checks.items() if not ok]
        if missing and now-last_report > 5.:
            print('Waiting for: ' + '; '.join(missing), flush=True)
            last_report = now
        if not missing:
            print('READY: clock, joints, camera, controllers and actions are available.', flush=True)
            break
    else:
        print('NOT READY: ' + '; '.join(missing), flush=True)
        print('Resume Gazebo if paused; otherwise stop/start the simulation and inspect logs/sim.log.', flush=True)
        raise SystemExit(1)
finally:
    node.destroy_node()
    rclpy.shutdown()
