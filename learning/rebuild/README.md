# 从零组装 CloudGrasp：代码实践路线

这是给你自己逐步实现、测试的第二阶段课程。每天不限定进度，一关验收后再进入下一关。
你将复用 UR5/Robotiq 的模型与已有 MoveIt 配置，逐步组装系统；不是重新手写机械臂网格、驱动或 MoveIt 求解器。
代码在 `cloudgrasp_lab/`，构建后是独立 ROS 包。原 `cloudgrasp_sim` 和你改好的 0.22 米预抓取参数保留。
第 7 关提供独立编译的 src/task.cpp，明确由原验证版本改编作为完整对照；不是全新抓取算法。

## 怎样学习每一关

1. 读本关源码，先预测输出和运动效果。
2. 运行提供的参考实现，记录实际结果。
3. 按练习要求自己改一处代码，再构建和测试。
4. 用 `git diff -- learning/rebuild` 查看自己改动了什么。
5. 在 `notes/` 里写记录。不要把“能编译”当作“动作正确”。

## 目录与职责

```text
learning/rebuild/
  env.sh                         加载 ROS/工作空间；实验独立通信域
  lab.sh                         统一命令入口
  cloudgrasp_lab/
    CMakeLists.txt / package.xml  ROS 包与构建依赖
    launch/lab.launch.py         逐阶段加入功能，核心阅读文件
    launch/motion.launch.py      给 C++ 示例传入参数与机器人模型
    launch/task.launch.py        启动本包完整抓取参考程序
    worlds/01_table.sdf          世界、桌面和待抓取方块
    worlds/03_camera.sdf         独立 RGB-D 传感器模型
    src/lab_motion.cpp           MoveIt 目标→IK→规划→可选执行
    src/task.cpp                 完整抓取参考实现，独立编译为 lab_task
    scripts/joint.py             直接向轨迹控制器发送关节目标
    scripts/observe.py           查看关节/图像/点云元数据
    scripts/scene.py             Gazebo + MoveIt 障碍物增删
    scripts/perceive.py          仅请求视觉识别，输出位姿与尺寸
    scripts/reference_pick.py    lab_task 运行监督与物体位移验证
    scripts/ready.py             按阶段检查就绪条件
    scripts/runner.py            进程生命周期、退出清理
  .runtime/                     本实验日志和状态，Git 忽略
  notes/                        你的逐关实验记录
```

## 构建与运行规则

在云服务器执行，不在 Windows PowerShell 执行 Linux 路径命令。

```bash
cd /root/gpufree-data/cloudgrasp_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon build --symlink-install --packages-select cloudgrasp_lab --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cd src/CloudGrasp
```

终端 A 启动某关，保持打开；终端 B 执行练习。切换阶段前，在终端 A 按 Ctrl+C，等 `LAB_STOPPED`，然后启动下一关。
也可在项目根目录执行 `bash learning/rebuild/lab.sh stop`，之后等待终端 A 确认停止。
不要在抓取/运动途中切换阶段；先等动作结束。

本实验使用 `ROS_DOMAIN_ID=42` 与独立 `GZ_PARTITION`。`lab.sh` 自动加载；手动运行 ros2/gz 命令前，每个终端都执行：

```bash
source learning/rebuild/env.sh
```

原课程终端默认在 ROS 域 0，不能用它观察域 42 的实验。最好先用原 manage.py stop 关闭原演示，减少资源占用和窗口混淆。
`source` 后环境只影响当前终端和子进程；不要把域 42 写入系统全局配置。

## 关卡 1：加载机械臂，观察模型和关节状态

代码：`launch/lab.launch.py` 的 01 段、`worlds/01_table.sdf`。
复用模型入口：`cloudgrasp_sim/urdf/ur5_gripper.urdf.xacro`。

```bash
# 终端 A
bash learning/rebuild/lab.sh start 1
# 终端 B
source learning/rebuild/env.sh
ros2 node list
ros2 topic echo /joint_states --once
ros2 control list_controllers
```

理解三件事：robot_state_publisher 发布模型/TF；ros_gz_sim create 创建 Gazebo 实体；joint_state_broadcaster 发布反馈。
本关只激活状态广播器，不激活轨迹控制器，也不启动相机与 MoveIt。默认同时打开基础 RViz，显示 RobotModel，可勾选 TF 查看坐标轴；rviz:=false 可关闭它。第 4 关起改用带 MoveIt 面板的配置。不要在本关发送运动命令。
验收：Gazebo 看见 UR5+夹爪；收到关节消息；控制器列表符合阶段配置。
自己练习：给桌面换颜色，确认修改的是 visual，而不是机器人控制参数。

## 关卡 2：不经过 MoveIt，直接控制关节

代码：`scripts/joint.py` 与 launch 的 02 段。

```bash
bash learning/rebuild/lab.sh start 2
# 另一个终端，以下命令逐条等待完成
bash learning/rebuild/lab.sh joint wrist
bash learning/rebuild/lab.sh joint home
bash learning/rebuild/lab.sh joint close
bash learning/rebuild/lab.sh joint open
```

读懂 JointTrajectory 的 joint_names、positions、time_from_start，以及 FollowJointTrajectory 动作的接受和完成结果。
`wrist` 仅把 wrist_3 设为绝对 0.20 rad，其余机械臂关节保持当前反馈位置；不是每次累加。运动时间 4 秒。
直接关节控制绕过 MoveIt 碰撞规划，本关只在无新增障碍、初始姿态附近使用给定小动作；这不是任意姿态的避障控制器。
验收：Gazebo 有实际变化，返回 JOINT_OK；理解为何数组必须按 joint_names 对应。
自己练习：仅将 wrist 的 0.20 改成 0.10，预测角度差；Python 保存后新启动命令生效。

## 关卡 3：加入相机，观察数据和坐标系

代码：`worlds/03_camera.sdf`、launch 的 03 段、`scripts/observe.py`。

```bash
bash learning/rebuild/lab.sh start 3
bash learning/rebuild/lab.sh observe
source learning/rebuild/env.sh
ros2 topic hz /camera/points
# Ctrl+C 只停止 hz 查看
ros2 run tf2_ros tf2_echo world camera_link
```

验收：图像 320×240；点云 frame 为 camera_link；收到 XYZ 等字段；理解这些只是元数据，不是物体检测结果。
GUI 观察相机与 RGB-D 传感器是两件事。实际传感器 pose 与静态 TF 必须一致；本 launch 从相机 SDF 同一处 pose 同时生成创建参数和 TF，避免两处手写不一致。
自己练习：把相机更新率从 10 改成 5，重启本关并观察频率。做完可恢复为 10。
不要只改 TF 假装移动相机；真实双目硬件接入需要深度/点云生成与标定，是后续单独课题。

## 关卡 4：使用 MoveIt，区分规划与执行

代码：`src/lab_motion.cpp`、`launch/motion.launch.py`、launch 的 04 段。

```bash
bash learning/rebuild/lab.sh start 4
# 另一个终端：默认只规划
bash learning/rebuild/lab.sh move
# 规划与实际执行
bash learning/rebuild/lab.sh move execute:=true
# 返回初始姿态
bash learning/rebuild/lab.sh move target:=home execute:=true
```

move 命令会先把已有物理桌面同步为 MoveIt 碰撞物体。目标默认为世界 (0.45,0.15,0.245) 米，固定朝向朝下。
读懂 setPoseReferenceFrame、setEndEffectorLink、set_target 中的 IK 求解、setJointValueTarget、plan、execute 和速度缩放。
验收：PLAN_ONLY 时 Gazebo 不动，可在 RViz 观察规划；EXECUTION_OK 时关节实际运动。
自己练习：仅规划 `z:=0.28`，观察轨迹，确认通过后才加 `execute:=true`。
C++ 修改必须重新构建 cloudgrasp_lab；修改运行参数则不需要编译。

## 关卡 5：增加障碍物，对比规划场景和物理场景

代码：`scripts/scene.py`。此脚本使用同一组尺寸和位置，分别写入 Gazebo 与 MoveIt。

```bash
bash learning/rebuild/lab.sh start 5
bash learning/rebuild/lab.sh scene table
bash learning/rebuild/lab.sh scene add
bash learning/rebuild/lab.sh scene list
bash learning/rebuild/lab.sh move
bash learning/rebuild/lab.sh scene remove
```

验收：Gazebo 与 RViz 都出现障碍物；场景列表含 lab_obstacle。添加在侧面的障碍物未必改变轨迹，这取决于它是否影响路径，不要把“轨迹没变”直接判为失败。
再做确定的反例：在机器人仍在 home 时运行以下命令，不执行被阻挡目标的运动。

```bash
bash learning/rebuild/lab.sh scene block
bash learning/rebuild/lab.sh move
# 预期报无碰撞 IK 无解或 PLAN_FAILED：障碍物覆盖目标夹爪区域
bash learning/rebuild/lab.sh scene remove
bash learning/rebuild/lab.sh move
# 移除后应可重新规划
```

不要连续 add/block 而不 remove；重复模型名将拒绝创建。
规划物体不等于物理物体；只改一边会出现“不知道障碍”或“看不见却绕行”的不一致。
自己练习：修改 add 模式的障碍物 XY，观察它在何处开始影响路径；每次先 remove 再 add。

## 关卡 6：视觉定位，不执行抓取

代码：launch 的 06 段与 `scripts/perceive.py`。
底层算法复用 `simple_grasping_ros2/simple_grasping`；本关实现的是输入连接与请求/结果消费。

```bash
bash learning/rebuild/lab.sh start 6
bash learning/rebuild/lab.sh reset
bash learning/rebuild/lab.sh perceive
```

验收：动作 plan_grasps=False；输出 world 坐标中的候选物体；用尺寸与工作区域区分方块和机器人点簇；机械臂不运动。
自己练习：在 perceive.py 输出阶段添加你自己的尺寸筛选和“选中目标”提示，先不连接任何运动。
不要直接把列表第一项当作方块，也不要读取 Gazebo 真值作为抓取目标。

## 关卡 7：组装自己的抓取状态流程，对照参考实现

```bash
bash learning/rebuild/lab.sh start 7
bash learning/rebuild/lab.sh reset
bash learning/rebuild/lab.sh pick
```

这个 pick 运行本包独立编译的 lab_task（src/task.cpp），再用 Gazebo 位移验证。完整源码由原验证版本改编并保留 0.22 米预抓取偏移，用作你的实现对照。
源码对照：`cloudgrasp_sim/src/vision_pick_place.cpp`；监督与报告入口：`scripts/reference_pick.py`。
接下来由你阅读现有 task.cpp，并新建自己的 my_task.cpp，按以下顺序实现，每完成一步再测试：

1. 仅请求视觉目标并打印；失败就退出。
2. 选择合法目标，构造 TCP 预抓取位姿；仅规划。
3. 执行到预抓取位置，再返回 home，暂不下降。
4. 添加完整笛卡尔下降路径；路径不完整不执行。
5. 闭合夹爪并抬升；先观察真实物体是否跟随。
6. 添加 MoveIt 附着物体；明确它不提供物理吸附。
7. 转移、下降、释放、移除附着物体、撤离、回 home。
8. 接入超时、阶段日志、执行错误处理和独立位移报告。

把 my_task.cpp 作为新目标加入 CMakeLists.txt，再参照已有 task.launch.py 编写 my_task.launch.py。
这些分步实现由你亲手完成；现有 lab_motion.cpp 和原 vision_pick_place.cpp 分别提供小例子与完整对照。
提供的完整参考代码没有待填 TODO；你的逐步练习请放在 my_task.cpp 中，保留可运行对照。

## 故障与结果记录

`.runtime/sim.log`：当前实验启动日志；参考 pick 的日志/JSON 也在 `.runtime/`。
检查某一关：`bash learning/rebuild/lab.sh ready 3 --timeout 10`（替换为当前阶段）。
切换阶段失败先检查旧终端是否输出 LAB_STOPPED；不要把实验域 42 的 ros2 命令与原域 0 混用。

每关记录：代码改了什么、预期现象、实际输出、是否满足验收、问题原因与修复。验证过的范围见 `VALIDATION.md`。

基础 RViz 配置在 cloudgrasp_lab/config/robot.rviz。它通过 /robot_description 加载模型，通过 TF 显示各连杆位置，不需要 MoveIt。注意始终在 /root/gpufree-data/cloudgrasp_ws 中构建，避免在 learning/rebuild 内生成第二套 build/install/log。

## 滑条与按钮控制

阶段 2 已支持桌面控制面板：`bash learning/rebuild/lab.sh panel`。具体使用与代码讲解见 [CONTROL_PANEL.md](CONTROL_PANEL.md)。
