# 第 3 课：读懂启动过程

## 目标

沿着 manage.py start → start.sh → sim.launch.py 阅读实际代码，理解环境加载、模块启动与就绪检查的关系。本课先只读，不修改代码，也不必启动仿真。

## 第一阶段：找到启动入口

在云服务器 VS Code 打开项目 /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp。
打开 cloudgrasp_sim/scripts/manage.py，搜索 if action == 'start':。

关键代码：

```python
action = sys.argv[1] if len(sys.argv) > 1 else 'status'
```

运行 /usr/bin/python3 cloudgrasp_sim/scripts/manage.py start 时，sys.argv[0] 是脚本路径，sys.argv[1] 是 start；没有提供参数时默认为 status。
if action == 'start': 根据参数进入启动分支。running() 检查已记录的仿真管理进程是否仍存在；已有实例则检查就绪，否则清理匹配的残留服务，再启动 start.sh。

```python
process = subprocess.Popen(['bash', str(HERE / 'start.sh')], ...)
```

这里省略了输出重定向等参数，阅读时以源文件完整代码为准。Popen 创建子进程运行 Bash 脚本，不会等整个仿真结束才继续执行。后续写入 PID 并调用 ready(45)，检查各模块在限定时间内是否就绪。

职责：manage.py 管理启动、停止、状态和进程；start.sh 加载运行环境并调用 ROS 2 launch；sim.launch.py 描述需要启动的节点及参数。
GZ_PARTITION 仅隔离 Gazebo Transport 通信，不会自动隔离 ROS 2 通信。

## 进度

- 已核对服务器现有 manage.py 和 start.sh。
- 当前步骤：学员已识别 Popen 调用 start.sh；接下来阅读 start.sh 的环境加载与 ros2 launch 命令。
- [x] 找到命令参数与启动分支。
- [x] 解释 manage.py 如何调用 start.sh。
- [x] 解释 start.sh 如何加载环境并调用 launch。
- [x] 在 sim.launch.py 找到机器人生成、控制器、感知与 MoveIt。
- [x] 解释进程运行与系统就绪的区别。

后续按实际学习反馈追加记录。

## 启动入口复盘

学员正确回答 Popen 通过 bash 调用 start.sh。接下来在 VS Code 打开 cloudgrasp_sim/scripts/start.sh，重点阅读两条 source 和最后的 exec ros2 launch。

source /opt/ros/jazzy/setup.bash 加载 ROS 2 Jazzy 环境；source "$WS/install/setup.bash" 加载当前工作空间已安装的软件包环境。WS 是脚本计算出的工作空间路径。最后 exec ros2 launch cloudgrasp_sim sim.launch.py "$@" 启动 cloudgrasp_sim 包的 sim.launch.py；exec 用新程序替换当前 Bash 进程，额外脚本参数通过 "$@" 传递。DISPLAY 选择图形显示，GZ_PARTITION 设置本次 Gazebo 通信分区，session.env 保存分区供其他脚本使用。

下一问：最后一行中哪个是软件包名，哪个是 launch 文件名？等待学员回答后验收。

## ROS 2 launch 命令复盘

学员正确指出 cloudgrasp_sim 是软件包名，sim.launch.py 是启动文件名。下一步打开 cloudgrasp_sim/launch/sim.launch.py，定位 robot_state_publisher 的 Node 配置，学习 package、executable 和 parameters。package 指可执行程序所属 ROS 软件包，executable 指运行的程序，parameters 提供该节点的参数。启动文件所属包与其启动的节点所属包可以不同。此处 robot_state_publisher 接收 config.robot_description 和 sim（use_sim_time=True）参数。节点实例名称可能受程序默认值或 name 参数影响，不能普遍等同于 executable。

## MoveIt 启动配置复盘

学员正确回答 package 为 moveit_ros_move_group，executable 为 move_group。暂停后续阅读，先修复 VS Code 头文件解析环境。

## VS Code 头文件解析修复

发现项目没有 .vscode 配置和 compile_commands.json。已开启 CMAKE_EXPORT_COMPILE_COMMANDS 并完成全部 6 个包构建，生成工作空间 build/compile_commands.json，包含 14 条编译记录。新增 .vscode/c_cpp_properties.json 与 settings.json，使 C++ 扩展使用实际编译参数；新终端使用 ros.bashrc 自动加载 Jazzy 和工作空间环境。build.sh 已保留编译数据库导出参数。
验证：全工作空间构建通过，主抓取源码使用数据库原始编译参数执行 -fsyntax-only 通过。若旧的红色波浪线未立即消失，使用命令面板 C/C++: Reset IntelliSense Database，再执行 Developer: Reload Window。此项为编辑器配置修复，不更改抓取逻辑。

## VS Code 修复确认与恢复学习

学员确认头文件解析已修好，继续第 3 课。
下一步阅读 sim.launch.py 的视觉节点：package='simple_grasping'，executable='basic_grasping_perception_node'。重点学习 remappings=[('/wrist_rgbd_depth_sensor/points', '/camera/points')]：把节点原本使用的话题名重映射到本仿真提供的点云话题。这里改变通信名称，不转换点云内容或坐标系。
提问：如果仿真点云话题改为 /stereo/points，而感知程序内部话题名不变，应该修改这对映射中的哪一项？尚待回答。

## 话题重映射复盘：通过

学员正确回答 ('/wrist_rgbd_depth_sensor/points', '/stereo/points')。理解保留原始名称、替换运行时目标名称。本题为口头练习，未修改实际话题配置。

下一步阅读 controller_manager 包的 spawner 可执行程序。arguments 指定 joint_state_broadcaster、arm_controller、gripper_controller，及 --controller-manager-timeout 90。spawner 请求 controller_manager 加载、配置并激活这些控制器；它自身不是持续执行机械臂轨迹的控制器。90 表示等待 controller manager 服务可用的超时秒数，不是机械臂运动时长。
提问：为什么除 arm_controller 与 gripper_controller 外，还需要 joint_state_broadcaster？等待学员回答。

## 关节状态广播复盘：通过

学员解释需要广播机械臂各关节状态，供其他任务使用。理解正确。补充准确表述：joint_state_broadcaster 发布关节状态消息，其他节点订阅这些数据；例如 robot_state_publisher 计算连杆坐标变换，MoveIt 获取当前关节状态。

下一步阅读 ros_gz_sim 包的 create 程序。当前参数指定 world=cloudgrasp、模型名称=cloudgrasp、模型描述来源话题=robot_description、allow_renaming=false。该程序请求 Gazebo 在指定世界中创建机器人实体；读取模型描述的话题不同于持续更新关节位置的 /joint_states。关闭自动重命名不是清理旧后台进程的替代手段。
提问：这段 create 配置使用哪个话题获取机器人模型描述？等待回答。

## 机器人生成配置复盘：通过

学员正确回答 create 从 robot_description 话题获取机器人模型描述。已完成机器人生成、控制器、感知与 MoveIt 配置的定位练习。

下一步回到 manage.py 查看 ready(45)：创建启动子进程后，调用 ready.sh 和 preflight.py，等待仿真时钟推进、新鲜关节状态、新鲜相机点云、控制器激活以及 MoveIt/感知动作服务可用。45 是新实例启动就绪检查的超时秒数，不是固定睡眠或机械臂运动时间；条件满足就提前返回。已有实例的检查使用 ready(8)。这些检查是启动必要条件，不能替代后续物理抓取验证。
提问：为什么 Gazebo 和 RViz 窗口已经出现，还要等待 READY 才开始抓取？等待回答。

## 就绪检查复盘：通过

学员回答：程序看起来已打开，但仿真内部还未准备好。理解正确；界面出现不能证明控制器激活、时钟推进、关节状态和点云更新、动作服务可用。
当前已完成各模块和就绪检查的阅读，最后用口头练习串联命令分支：运行 manage.py stop 时，action 的值是什么，会进入哪个条件分支？此项用于确认命令参数与分支关系，尚待回答。

## 第 3 课最终复盘：完成

学员回答 action 为 stop，随后调用 stop_group(pid)。已补充区分：先进入 elif action == stop 分支，running() 找到实例后才调用停止函数；找不到实例则检查残留服务。第 3 课全部验收完成。
