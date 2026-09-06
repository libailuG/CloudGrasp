"""Stage 02: send a small joint trajectory directly; this bypasses MoveIt collision planning."""
import argparse, time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus
from common import wait
p=argparse.ArgumentParser();p.add_argument('mode',choices=['wrist','home','open','close']);a=p.parse_args()
rclpy.init();n=rclpy.create_node('lab_joint_command');latest={};last_feedback=[0.0]
def state(msg):
    latest.update(zip(msg.name,msg.position));last_feedback[0]=time.monotonic()
n.create_subscription(JointState,'/joint_states',state,qos_profile_sensor_data)
arm=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
names=arm if a.mode in ['wrist','home'] else ['robotiq_85_left_knuckle_joint']
client=ActionClient(n,FollowJointTrajectory,('/arm_controller' if len(names)>1 else '/gripper_controller')+'/follow_joint_trajectory')
handle=None
try:
    end=time.monotonic()+8
    while not all(k in latest for k in names):
        if time.monotonic()>end: raise TimeoutError('No joint feedback')
        rclpy.spin_once(n,timeout_sec=.1)
    if not client.wait_for_server(timeout_sec=8): raise RuntimeError('Controller unavailable; start stage 2 or later')
    before={k:latest[k] for k in names}
    values=[latest[k] for k in names]
    if a.mode=='wrist': values[-1]=0.20 # absolute 0.20 rad; repeat does not accumulate rotation
    elif a.mode=='home': values=[-1.57,-1.57,1.57,-1.57,-1.57,0.]
    else: values=[0.0 if a.mode=='open' else 0.48]
    goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=names
    point=JointTrajectoryPoint();point.positions=values;point.time_from_start.sec=4
    goal.trajectory.points=[point]
    handle=wait(n,client.send_goal_async(goal))
    if not handle.accepted: raise RuntimeError('Trajectory rejected')
    result=wait(n,handle.get_result_async(),20)
    if result.status!=GoalStatus.STATUS_SUCCEEDED or result.result.error_code!=0:
        raise RuntimeError(f'Trajectory failed: {result.result.error_string}')
    # Action success and requested positions alone are not a measurement.
    finished=time.monotonic()
    while last_feedback[0]<=finished:
        if time.monotonic()-finished>3:raise TimeoutError('No fresh feedback after execution')
        rclpy.spin_once(n,timeout_sec=.1)
    actual={k:latest[k] for k in names}
    error=max(abs(actual[k]-v) for k,v in zip(names,values))
    if error>0.01:raise RuntimeError(f'Final joint feedback differs from target by {error:.4f} rad')
    print('JOINT_OK (feedback verified)')
    changed=names if a.mode!='wrist' else ['wrist_3_joint']
    for k in changed:
        print(f'  {k}: before={before[k]:.4f}, target={values[names.index(k)]:.4f}, actual={actual[k]:.4f}, delta={actual[k]-before[k]:+.4f} rad')
    if max(abs(actual[k]-before[k]) for k in names)<0.001:
        print('ALREADY_AT_TARGET: absolute target unchanged; no visible motion expected.')
except (Exception,KeyboardInterrupt):
    if handle is not None and handle.accepted:
        try: wait(n,handle.cancel_goal_async(),2)
        except Exception: pass
    raise
finally:
    client.destroy();n.destroy_node();rclpy.shutdown()
