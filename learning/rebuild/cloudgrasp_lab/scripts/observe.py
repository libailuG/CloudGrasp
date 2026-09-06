"""Stage 03: inspect metadata, not thousands of raw point values."""
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState,PointCloud2,Image
rclpy.init();n=rclpy.create_node('lab_observer');seen=set()
def joints(m):
    if 'joints' not in seen:
        print('JOINTS',dict(zip(m.name,m.position)));seen.add('joints')
def cloud(m):
    if 'cloud' not in seen:
        print('CLOUD frame=',m.header.frame_id,'size=',(m.width,m.height),'fields=',[f.name for f in m.fields]);seen.add('cloud')
def image(m):
    if 'image' not in seen:
        print('IMAGE',m.width,m.height,m.encoding);seen.add('image')
n.create_subscription(JointState,'/joint_states',joints,qos_profile_sensor_data)
n.create_subscription(PointCloud2,'/camera/points',cloud,qos_profile_sensor_data)
n.create_subscription(Image,'/camera/image',image,qos_profile_sensor_data)
end=time.monotonic()+12
while len(seen)<3 and time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.1)
n.destroy_node();rclpy.shutdown()
if len(seen)<3:raise SystemExit('Missing streams: '+str({'joints','cloud','image'}-seen))
