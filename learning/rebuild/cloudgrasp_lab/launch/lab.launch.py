"""Read in order: robot -> controllers -> sensor -> MoveIt -> perception."""
from pathlib import Path
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def setup(context):
    stage = int(LaunchConfiguration('stage').perform(context))
    if stage not in range(1, 8):
        raise ValueError('stage must be 1..7')
    gui = LaunchConfiguration('gui').perform(context) == 'true'
    rviz = LaunchConfiguration('rviz').perform(context) == 'true'
    lab, assets = Path(share('cloudgrasp_lab')), Path(share('cloudgrasp_sim'))
    c = (MoveItConfigsBuilder('cloudgrasp', package_name='cloudgrasp_sim')
         .robot_description(file_path='urdf/ur5_gripper.urdf.xacro')
         .robot_description_semantic(file_path='config/cloudgrasp.srdf')
         .robot_description_kinematics(file_path='config/kinematics.yaml')
         .joint_limits(file_path='config/joint_limits.yaml')
         .trajectory_execution(file_path='config/moveit_controllers.yaml')
         .planning_pipelines(pipelines=['ompl']).to_moveit_configs())
    sim = {'use_sim_time': True}
    def gz(args):
        return IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(Path(share('ros_gz_sim'))/'launch/gz_sim.launch.py')),
            launch_arguments={'gz_args': args, 'on_exit_shutdown': 'true'}.items())
    # 01: Publish robot model/TF, create its physical entity, publish joint feedback.
    nodes = [gz(['-r -s ', str(lab/'worlds/01_table.sdf')]),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[c.robot_description, sim], output='screen'),
        Node(package='ros_gz_sim', executable='create', arguments=[
             '-world','cloudgrasp','-name','cloudgrasp','-topic','robot_description',
             '-allow_renaming','false'], output='screen')]
    controllers = ['joint_state_broadcaster']
    # 02: Add command interfaces; stage 01 intentionally has no trajectory controllers active.
    if stage >= 2:
        controllers += ['arm_controller', 'gripper_controller']
    nodes.append(Node(package='controller_manager', executable='spawner',
        arguments=controllers+['--controller-manager-timeout','60'], output='screen'))
    bridge = ['/world/cloudgrasp/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock']
    # 03: Camera is a separate model: you can edit its SDF independently.
    if stage >= 3:
        cp = ET.parse(lab/'worlds/03_camera.sdf').findtext('model/pose').split()
        nodes += [Node(package='ros_gz_sim', executable='create', arguments=[
            '-world','cloudgrasp','-file',str(lab/'worlds/03_camera.sdf'),
            '-x',cp[0],'-y',cp[1],'-z',cp[2],'-R',cp[3],'-P',cp[4],'-Y',cp[5],
            '-allow_renaming','false'], output='screen'),
            Node(package='tf2_ros', executable='static_transform_publisher', arguments=[
            '--x',cp[0],'--y',cp[1],'--z',cp[2],'--roll',cp[3],'--pitch',cp[4],'--yaw',cp[5],
            '--frame-id','world','--child-frame-id','camera_link'])]
        bridge += ['/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo']
    nodes.append(Node(package='ros_gz_bridge', executable='parameter_bridge',
        arguments=bridge, remappings=[('/world/cloudgrasp/clock','/clock')], output='screen'))
    # 04/05: Planning server; the scene.py exercise adds the table and obstacles.
    if stage >= 4:
        nodes.append(Node(package='moveit_ros_move_group', executable='move_group',
            parameters=[c.to_dict(),sim,{'publish_robot_description_semantic': True}], output='screen'))
    # RViz is a viewer in every stage; only later stages use its MoveIt panel.
    if rviz:
        display = assets/'config/demo.rviz' if stage >= 4 else lab/'config/robot.rviz'
        params = [c.to_dict(),sim] if stage >= 4 else [c.robot_description,sim]
        nodes.append(Node(package='rviz2', executable='rviz2',
            arguments=['-d',str(display)],parameters=params,output='screen'))
    # 06/07: Perception first, then the complete reference grasp as a separate command.
    if stage >= 6:
        nodes.append(Node(package='simple_grasping', executable='basic_grasping_perception_node',
            parameters=[sim,{'debug_topics':True,'frame_id':'world','range_field_name':'x',
                'voxel_leaf_size':0.003,'voxel_limit_min':-0.01,'voxel_limit_max':0.25}],
            remappings=[('/wrist_rgbd_depth_sensor/points','/camera/points')],output='screen'))
    if gui:
        nodes.append(gz(['-g --gui-config ', str(assets/'config/gazebo_gui.config')]))
    return nodes


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('stage',default_value='1'),
        DeclareLaunchArgument('gui',default_value='true'),
        DeclareLaunchArgument('rviz',default_value='true'), OpaqueFunction(function=setup)])
