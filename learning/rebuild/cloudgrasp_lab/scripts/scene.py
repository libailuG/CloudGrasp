"""Stage 05: same obstacle geometry in Gazebo and MoveIt; table exists in Gazebo already."""
import argparse, subprocess
import rclpy
from moveit_msgs.srv import ApplyPlanningScene,GetPlanningScene
from moveit_msgs.msg import CollisionObject,PlanningSceneComponents
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose
from common import wait
p=argparse.ArgumentParser();p.add_argument('mode',choices=['table','add','block','remove','list']);a=p.parse_args()
rclpy.init();n=rclpy.create_node('lab_scene')

def apply(obj):
    c=n.create_client(ApplyPlanningScene,'/apply_planning_scene')
    if not c.wait_for_service(timeout_sec=10):raise RuntimeError('MoveIt unavailable')
    r=ApplyPlanningScene.Request();r.scene.is_diff=True;r.scene.world.collision_objects=[obj]
    if not wait(n,c.call_async(r)).success:raise RuntimeError('Planning scene rejected')

def box(name,xyz,dims):
    o=CollisionObject();o.header.frame_id='world';o.id=name;o.operation=CollisionObject.ADD
    b=SolidPrimitive();b.type=SolidPrimitive.BOX;b.dimensions=dims
    pose=Pose();pose.orientation.w=1.;pose.position.x,pose.position.y,pose.position.z=xyz
    o.primitives=[b];o.primitive_poses=[pose];return o

def gz(req,kind,service):
    r=subprocess.run(['gz','service','-s',service,'--reqtype',kind,'--reptype','gz.msgs.Boolean','--timeout','5000','--req',req],capture_output=True,text=True,timeout=8)
    if r.returncode or 'true' not in r.stdout:raise RuntimeError('Gazebo request failed: '+r.stdout+r.stderr)

try:
    if a.mode=='list':
        c=n.create_client(GetPlanningScene,'/get_planning_scene')
        if not c.wait_for_service(timeout_sec=8):raise RuntimeError('MoveIt unavailable')
        q=GetPlanningScene.Request();q.components.components=PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
        print('SCENE_OBJECTS',[o.id for o in wait(n,c.call_async(q)).scene.world.collision_objects])
    elif a.mode=='table':
        apply(box('table',[.25,0.,-.035],[1.7,1.5,.07]));print('TABLE_OK')
    elif a.mode=='remove':
        gz('name: "lab_obstacle", type: MODEL','gz.msgs.Entity','/world/cloudgrasp/remove')
        o=CollisionObject();o.id='lab_obstacle';o.operation=CollisionObject.REMOVE;apply(o);print('OBSTACLE_REMOVED')
    else:
        # Normal obstacle stays away from home; block deliberately covers the pose target.
        xyz=[.60,-.25,.15] if a.mode=='add' else [.45,.15,.245]
        dims=[.12,.12,.30] if a.mode=='add' else [.18,.18,.18]
        # Adding twice is rejected rather than silently creating mismatched obstacle geometry.
        pose=' '.join(map(str,xyz))+' 0 0 0';size=' '.join(map(str,dims))
        sdf=f'<sdf version="1.9"><model name="lab_obstacle"><static>true</static><pose>{pose}</pose><link name="link"><collision name="c"><geometry><box><size>{size}</size></box></geometry></collision><visual name="v"><geometry><box><size>{size}</size></box></geometry><material><diffuse>0.95 0.65 0.05 1</diffuse></material></visual></link></model></sdf>'
        import json
        gz('sdf: '+json.dumps(sdf)+', allow_renaming: false','gz.msgs.EntityFactory','/world/cloudgrasp/create')
        try:apply(box('lab_obstacle',xyz,dims))
        except Exception:
            gz('name: "lab_obstacle", type: MODEL','gz.msgs.Entity','/world/cloudgrasp/remove');raise
        print('OBSTACLE_OK',xyz,dims,'(Gazebo + MoveIt)')
finally:n.destroy_node();rclpy.shutdown()
