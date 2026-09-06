from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    c=(MoveItConfigsBuilder('cloudgrasp',package_name='cloudgrasp_sim')
       .robot_description(file_path='urdf/ur5_gripper.urdf.xacro')
       .robot_description_semantic(file_path='config/cloudgrasp.srdf')
       .robot_description_kinematics(file_path='config/kinematics.yaml').planning_pipelines(pipelines=['ompl']).to_moveit_configs())
    return LaunchDescription([
        DeclareLaunchArgument('target', default_value='pose'),
        DeclareLaunchArgument('execute', default_value='false'),
        DeclareLaunchArgument('x', default_value='0.45'),
        DeclareLaunchArgument('y', default_value='0.15'),
        DeclareLaunchArgument('z', default_value='0.245'),
        Node(package='cloudgrasp_lab',executable='lab_motion',parameters=[
            c.robot_description,c.robot_description_semantic,c.robot_description_kinematics,
            {'use_sim_time':True, 'target':LaunchConfiguration('target'),
             'execute':ParameterValue(LaunchConfiguration('execute'),value_type=bool),
             **{k:ParameterValue(LaunchConfiguration(k),value_type=float) for k in ['x','y','z']}}],output='screen')])
