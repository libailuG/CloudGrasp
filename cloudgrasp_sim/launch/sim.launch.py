from pathlib import Path
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    p = Path(get_package_share_directory('cloudgrasp_sim'))
    config = (MoveItConfigsBuilder('cloudgrasp', package_name='cloudgrasp_sim')
      .robot_description(file_path='urdf/ur5_gripper.urdf.xacro')
      .robot_description_semantic(file_path='config/cloudgrasp.srdf')
      .robot_description_kinematics(file_path='config/kinematics.yaml')
      .joint_limits(file_path='config/joint_limits.yaml')
      .trajectory_execution(file_path='config/moveit_controllers.yaml')
      .planning_pipelines(pipelines=['ompl']).to_moveit_configs())
    sim = {'use_sim_time': True}
    return LaunchDescription([
      DeclareLaunchArgument('rviz', default_value='true'),
      DeclareLaunchArgument('gui', default_value='true'),
      IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(get_package_share_directory('ros_gz_sim'))/'launch/gz_sim.launch.py')), launch_arguments={'gz_args': ['-r -s ', str(p/'worlds/tabletop.sdf')], 'on_exit_shutdown': 'true'}.items()),
      Node(package='ros_gz_sim', executable='create', arguments=['-world','cloudgrasp','-name','cloudgrasp','-topic','robot_description','-allow_renaming','false'], output='screen'),
      Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[config.robot_description, sim], output='screen'),
      Node(package='ros_gz_bridge', executable='parameter_bridge', arguments=['/world/cloudgrasp/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock','/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked','/camera/image@sensor_msgs/msg/Image[gz.msgs.Image','/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image','/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo'], parameters=[sim], remappings=[('/world/cloudgrasp/clock','/clock')], output='screen'),
      Node(package='tf2_ros', executable='static_transform_publisher', arguments=['--x','0.45','--y','0.05','--z','1.1','--roll','0','--pitch','1.57079632679','--yaw','0','--frame-id','world','--child-frame-id','camera_link']),
      Node(package='controller_manager', executable='spawner', arguments=['joint_state_broadcaster','arm_controller','gripper_controller','--controller-manager-timeout','90'], parameters=[sim], output='screen'),
      Node(package='moveit_ros_move_group', executable='move_group', parameters=[config.to_dict(),sim,{'publish_robot_description_semantic':True}], output='screen'),
      Node(package='simple_grasping', executable='basic_grasping_perception_node', parameters=[sim,{'debug_topics':True,'frame_id':'world','range_field_name':'x','voxel_leaf_size':0.003,'voxel_limit_min':-0.01,'voxel_limit_max':0.25}], remappings=[('/wrist_rgbd_depth_sensor/points','/camera/points')],output='screen'),
      Node(package='rviz2', executable='rviz2', arguments=['-d',str(p/'config/demo.rviz')],parameters=[config.to_dict(),sim],condition=IfCondition(LaunchConfiguration('rviz')),output='screen'),
      IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(get_package_share_directory('ros_gz_sim'))/'launch/gz_sim.launch.py')),launch_arguments={'gz_args':['-g --gui-config ', str(p/'config/gazebo_gui.config')]}.items(),condition=IfCondition(LaunchConfiguration('gui'))),
    ])
