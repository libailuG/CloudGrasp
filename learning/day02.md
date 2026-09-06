# 第 2 天：ROS 2 节点与话题

## 目标

查看运行中的节点和话题，理解发布者与订阅者，并观察关节状态与相机点云。
本课先做只读检查，不发送机械臂运动命令。

## 第 1 步：启动系统并查看节点

在云服务器终端 A 执行：

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py start
```

等待 READY。然后打开云服务器终端 B，执行：

```bash
source /opt/ros/jazzy/setup.bash
source /root/gpufree-data/cloudgrasp_ws/install/setup.bash
ros2 node list
```

source 将 ROS 和工作空间环境加载到当前终端。启动脚本中的环境设置不会自动传回父终端，因此新终端需要单独加载。
节点是 ROS 2 中承担某项功能的通信单元，例如发布机器人坐标变换、处理点云、规划运动。同一个进程可以包含多个节点，节点不等于操作系统进程。
ros2 node list 只列出当前可发现的节点，不会让机械臂运动。

## 后续步骤（根据实际反馈逐步讲解）

1. 从实际输出中辨认机器人描述、规划和感知相关节点。
2. ros2 topic list：查看数据通道。
3. ros2 topic info /joint_states -v：查看关节状态的发布者与订阅者。
4. ros2 topic echo /joint_states --once：读取一条关节状态消息。
5. ros2 topic hz /camera/points：观察点云接收频率，Ctrl+C 结束查看。

## 进度与验收

- 当前进度：第 2 课完成；节点、话题、关节状态、发布订阅与点云频率的练习和复盘均已通过。
- [x] 查看节点列表并指出至少两个节点的作用。
- [x] 找到 /joint_states 和 /camera/points。
- [x] 理解话题发布者与订阅者的关系。
- [x] 读取一条关节状态消息并解释 name、position。
- [x] 观察相机点云频率。

实际命令输出、问题和概念复盘将随学习过程追加；尚未完成的操作不提前标记。

## 节点列表：学员实际反馈

```text
/arm_controller
/basic_grasping_perception
/controller_manager
/gripper_controller
/gz_ros_control
/interactive_marker_display_93973794452576
/joint_state_broadcaster
/move_group
/move_group/moveit
/move_group_private_94457313590880
/moveit_1713222237
/moveit_3026148603
/moveit_simple_controller_manager
/robot_state_publisher
/ros_gz_bridge
/rviz
/rviz_private_140497240162960
/static_transform_publisher_FpRDPt9hfNL6Ko98
/transform_listener_impl_5577fa3d8440
/transform_listener_impl_55e88ebe46b0
/transform_listener_impl_56109a531610
/transform_listener_impl_7fc81028baf0
```

核心节点解释：
- basic_grasping_perception：处理点云，检测可抓取物体。
- move_group：MoveIt 的规划与执行协调节点。
- arm_controller：执行机械臂关节轨迹。
- gripper_controller：控制夹爪关节。
- controller_manager：加载、激活和管理控制器。
- gz_ros_control：连接 Gazebo 仿真关节与 ros2_control。
- joint_state_broadcaster：发布关节状态。
- robot_state_publisher：根据机器人模型和关节位置，发布连杆之间的坐标变换。
- ros_gz_bridge：桥接配置的 Gazebo 与 ROS 数据，如时钟和相机数据；机械臂关节控制由 gz_ros_control 连接。
- rviz：可视化机器人、规划和传感器等数据。

带数字后缀的名称常由程序运行时生成；名称本身不能证明存在残留进程。不要求记忆所有内部节点。
注意：node list 显示节点被发现，不等于所有节点功能正常，也不等于抓取已就绪。

下一步在已加载 ROS 环境的同一终端执行 ros2 topic list。话题是具名的数据通道，节点通过发布和订阅交换消息。等待学员反馈实际话题列表后继续讲解。

## 读取关节状态：学员实际反馈

已执行 ros2 topic echo /joint_states --once，收到包含 12 个关节的消息。时间戳为 298.620000000，frame_id 为 base_link。
机械臂主要关节位置（rad）：elbow_joint=1.5700279，shoulder_lift_joint=-1.5700002，shoulder_pan_joint=-1.5700000，wrist_1_joint=-1.5700338，wrist_2_joint=-1.5700000，wrist_3_joint=1.3465e-08。夹爪关节约为正负 0.0002 rad。各关节速度接近零，effort 均为 NaN。

解释：name、position、velocity、effort 按数组索引一一对应，不能假定所有机器人都采用相同关节顺序。当前这些关节是转动关节，位置单位 rad，速度单位 rad/s，力矩若有效则单位 N·m。约 1.57 rad 为 90 度；正负表示相对于关节定义轴的旋转方向。接近零的速度说明采样时基本静止。NaN 表示该消息未提供有效力矩数值，不代表力矩为零；仅凭消息不能确定具体未提供原因。

开头报告 A message was lost，计数为 1，但随后收到完整状态消息。这是接收链路报告一次消息丢失，不能据此认定机械臂控制失败；单次提示不影响本次字段学习。若持续出现，再检查通信、QoS 和系统负载。

学习进度：已读取一条状态消息；待学员解释关节对应关系。下一步执行 ros2 topic info /joint_states，查看消息类型、发布者数量和订阅者数量。

## 话题通信信息：学员实际反馈

```text
Type: sensor_msgs/msg/JointState
Publisher count: 1
Subscription count: 2
```

解释：sensor_msgs 是消息包，msg 表示消息类别，JointState 是类型名称，定义此前看到的 header、name、position、velocity、effort 等字段。当前发现 1 个发布端和 2 个订阅端；数量不代表消息条数，也不严格等于不同节点数量，因为一个节点可创建多个通信端点。订阅者各自接收消息，不是两者轮流分配消息。
下一步执行 ros2 topic info /joint_states -v 查看端点所属节点及 QoS；实际节点名称待反馈确认，不凭数量推断。

## 确认关节状态数据流

学员执行 ros2 topic info /joint_states -v，确认发布节点为 joint_state_broadcaster；订阅节点为 robot_state_publisher 和 move_group_private_94457313590880。

数据流：joint_state_broadcaster → /joint_states → robot_state_publisher / MoveIt 状态监视模块。前者结合机器人模型与关节位置发布连杆坐标变换，后者使用当前关节状态进行规划与执行相关检查。robot_state_publisher 名称中的 publisher 指它发布坐标变换，并不妨碍它同时订阅关节状态；发布或订阅角色要结合具体话题判断。

本次端点信息中发布端 RELIABLE、订阅端 BEST_EFFORT；仅有该差异不能判定通信配置错误，也不能据此断定此前单次消息丢失的原因。本阶段不展开 QoS。

下一步观察传感器数据：ros2 topic hz /camera/points，等待约 5～10 秒后 Ctrl+C，反馈 average rate 等输出。该命令测量本订阅端接收到消息的频率，并非机械臂控制频率，也不能单凭该数字确定相机内部采样频率。

## 相机点云频率：学员实际反馈

average rate 从约 9.984 Hz 变化到 9.781 Hz；观察范围约 9.758～9.991 Hz。最短接收间隔 0.086 s，最长由约 0.113 s 增至 0.210 s，最后 std dev 为 0.01581 s、window 为 93。

解释：本订阅端每秒接收到约 9.8～10 条点云消息，与当前仿真相机配置 10 Hz 接近。min/max 为统计窗口内相邻接收消息的时间间隔极值；std dev 为间隔的标准差；window 为用于统计的样本数，不是时间秒数。出现约 0.2 s 间隔说明接收节奏偶有波动，不能单凭这些数据确认丢帧、网络问题或相机故障。

下一步概念复盘：请学员解释为什么 /joint_states 可以同时供 robot_state_publisher 和 MoveIt 使用，并说明两者用途。节点作用、发布订阅关系和 JointState 字段解释的概念验收仍根据学员回答逐项确认。

## 发布订阅复盘：通过

学员将话题比作群聊，订阅者接收消息，并解释 robot_state_publisher 用关节状态推算机器人位姿，MoveIt 用它规划轨迹。已理解发布订阅关系及两个节点的主要用途。
补充：robot_state_publisher 结合关节位置与机器人模型，计算并发布连杆之间的坐标变换，不是仅凭 JointState 推算机器人在世界中的绝对位置；MoveIt 利用关节状态获知当前姿态，并结合运动目标、模型和碰撞场景规划轨迹。
尚待验收：JointState 的 name 与 position 对应关系。提问：若 name 第一个元素是 elbow_joint，position 第一个元素是 1.57，这代表什么？它是否是夹爪的空间 X 坐标？

## 关节数据复盘：通过

学员回答：elbow_joint 的位置是 1.57 弧度。回答正确；本关节是转动关节，因此该位置表示相对于关节零位的转角，约为 90 度，并非末端的空间坐标。
第 2 课全部完成。已学习 node list、topic list、topic echo --once、topic info、topic info -v、topic hz。下一课按计划阅读启动脚本，理解系统如何启动和连接；本次未替学员停止仿真。
