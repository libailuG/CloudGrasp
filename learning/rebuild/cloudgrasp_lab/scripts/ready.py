import argparse,time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,PointCloud2
from rosgraph_msgs.msg import Clock
from controller_manager_msgs.srv import ListControllers
p=argparse.ArgumentParser();p.add_argument('stage',type=int);p.add_argument('--timeout',type=float,default=40);a=p.parse_args()
rclpy.init();n=rclpy.create_node('lab_ready');seen={};stamp=None

def clock(m):
    global stamp
    s=(m.clock.sec,m.clock.nanosec)
    if stamp is not None and s!=stamp:seen['clock']=time.monotonic()
    stamp=s
n.create_subscription(Clock,'/clock',clock,qos_profile_sensor_data)
n.create_subscription(JointState,'/joint_states',lambda m:seen.update(joints=time.monotonic()) if m.position else None,qos_profile_sensor_data)
n.create_subscription(PointCloud2,'/camera/points',lambda m:seen.update(camera=time.monotonic()) if m.width else None,qos_profile_sensor_data)
c=n.create_client(ListControllers,'/controller_manager/list_controllers');future=None;last=0.;active=set()
end=time.monotonic()+a.timeout;missing=[]
while time.monotonic()<end:
    rclpy.spin_once(n,timeout_sec=.1);now=time.monotonic()
    if future is not None and future.done():
        r=future.result();active={x.name for x in r.controller if x.state=='active'} if r else set();future=None
    if future is not None and now-last>3:c.remove_pending_request(future);future.cancel();future=None
    if future is None and c.service_is_ready() and now-last>1:future=c.call_async(ListControllers.Request());last=now
    streams=['clock','joints']+(['camera'] if a.stage>=3 else [])
    missing=[k for k in streams if now-seen.get(k,0)>2]
    required={'joint_state_broadcaster'}|({'arm_controller','gripper_controller'} if a.stage>=2 else set())
    if not required<=active:missing.append('controllers')
    services={name for name,_ in n.get_service_names_and_types()}
    if a.stage>=4 and '/compute_ik' not in services:missing.append('MoveIt')
    if a.stage>=6 and '/find_objects/_action/send_goal' not in services:missing.append('perception')
    if not missing:break
n.destroy_node();rclpy.shutdown()
if missing:raise SystemExit('NOT_READY: '+', '.join(missing))
print('LAB_READY stage',a.stage)
