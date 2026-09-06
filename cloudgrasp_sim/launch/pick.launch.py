from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    c=(MoveItConfigsBuilder('cloudgrasp',package_name='cloudgrasp_sim').robot_description(file_path='urdf/ur5_gripper.urdf.xacro').robot_description_semantic(file_path='config/cloudgrasp.srdf').robot_description_kinematics(file_path='config/kinematics.yaml').planning_pipelines(pipelines=['ompl']).to_moveit_configs())
    return LaunchDescription([Node(package='cloudgrasp_sim',executable='vision_pick_place',parameters=[c.robot_description,c.robot_description_semantic,c.robot_description_kinematics,{'use_sim_time':True}],output='screen')])
