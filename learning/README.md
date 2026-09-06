# CloudGrasp 学习计划

目标：能够独立启动仿真、解释视觉抓取流程、修改一个抓取参数并验证结果。
按初学者安排，共 7 天，每天约 1～2 小时；没有完成当天验收就多练一天。
当前环境：Ubuntu 24.04、ROS 2 Jazzy、MoveIt 2、Gazebo Harmonic。
本阶段全部在仿真中练习。当前仿真使用 RGB-D 点云；真实双目接入留到后续。

## 第 1 天：独立完成一次抓取

阅读 `../cloudgrasp_sim/README.zh-CN.md` 的“云桌面使用”和“命令行”。
在服务器终端逐条执行，等待每一步完成：

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py start
# 等待 Simulation ready，再运行下一条
bash cloudgrasp_sim/scripts/pick.sh
# 等待 PHYSICAL_PICK_PLACE_PASS，再重置方块
bash cloudgrasp_sim/scripts/reset_cube.sh
# 最后结束仿真
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py stop
```

观察 RViz 和 Gazebo：RViz 用于展示机器人状态、规划场景等；Gazebo 模拟运动、碰撞和接触。
记录机械臂动作顺序：张开夹爪、回初始姿态、识别、靠近、下降、闭合、抬升、移动、放下、松开、撤离、回初始姿态。
验收：不依赖协助，完成启动、抓取、重置、停止；知道成功提示是什么。

## 第 2 天：理解 ROS 2 如何连接各模块

先启动仿真，再在另一个终端执行：

```bash
source /opt/ros/jazzy/setup.bash
source /root/gpufree-data/cloudgrasp_ws/install/setup.bash
ros2 node list
ros2 topic list
ros2 action list -t
ros2 topic echo /joint_states --once
ros2 topic hz /camera/points
# 查看一会儿频率后用 Ctrl+C 结束
```

学习节点、话题、服务、动作四个概念。结合项目解释：
- 节点：独立运行的功能模块。
- 话题：连续发布的数据，如关节状态、相机点云。
- 服务：请求与响应，如查询控制器状态。
- 动作：可反馈进度的任务，如运动规划与执行。

验收：找到 /joint_states、/camera/points、/clock，以及 /move_action 和 /find_objects；分别说明用途。

## 第 3 天：读懂项目启动过程

依次阅读：
1. `../cloudgrasp_sim/scripts/manage.py`
2. `../cloudgrasp_sim/scripts/start.sh`
3. `../cloudgrasp_sim/launch/sim.launch.py`
4. `../cloudgrasp_sim/scripts/preflight.py`

画出启动关系：Gazebo → 机器人生成与控制器；机器人描述 → MoveIt 和 RViz；相机点云 → 感知节点。
理解为何窗口出现后仍要等待 READY，以及 /clock 不更新为什么会影响运行。
验收：能指出机器人生成、点云桥接、控制器启动、MoveIt 启动分别在哪里配置。

## 第 4 天：理解坐标与视觉识别

阅读 `../cloudgrasp_sim/worlds/tabletop.sdf` 和 `../simple_grasping/src/basic_grasping_perception.cpp`。
重点学习 world、camera_link、机器人基座、末端坐标系，位置 XYZ 与姿态的区别。
梳理点云流程：读取点云 → 坐标变换与过滤 → 平面/物体处理 → 输出候选物体。
本项目 Gazebo 点云使用前向 X 的坐标约定，过滤参数为 range_field_name: x；不要直接套用其他相机的 Z 前向假设。
验收：在日志中找到识别出的物体位置，并与场景中方块初始位置约 (0.45, 0.15, 0.025) 米比较。
先理解差异来源，不要求检测位置与模型中心完全相等。

## 第 5 天：读懂机械臂如何运动

阅读 `../cloudgrasp_sim/src/` 中的抓取实现，并搜索日志中的 STAGE 对应代码。
学习关节目标、末端位姿、逆运动学、路径规划、轨迹执行、笛卡尔路径的区别。
结合一次运行，找出预抓取、接近、夹紧、抬升、转移和释放的实现。
理解 MoveIt 中的附着碰撞物体用于规划；Gazebo 中物体是否被抓起，要看真实接触与位移。
验收：能解释“规划成功”为什么不等于“抓取成功”，以及 PHYSICAL_PICK_PLACE_PASS 检查什么。

## 第 6 天：完成第一次小改动

先运行 git status，记录当前状态。阅读 `../cloudgrasp_sim/config/gazebo_gui.config`，只调整 GUI 的 camera_pose，观察视角变化。
一次只改一个量，记录修改前后效果。然后可在理解源码后，尝试小幅调整预抓取高度；不改变多个运动参数。
修改 C++ 后，在工作空间目录构建：

```bash
cd /root/gpufree-data/cloudgrasp_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon build --symlink-install --packages-select cloudgrasp_sim
```

构建成功后停止并重新启动仿真，再运行抓取验证。
验收：用 git diff 说明自己改了什么、为什么改、实际效果如何。
不要直接改变放置坐标：当前物理验证也检查放置位置，修改时需要一起理解并更新验证条件。

## 第 7 天：独立排查并复盘

阅读 `../cloudgrasp_sim/scripts/pick.sh`、`run_pick.py` 和 `watch_cube.py`。
做一次可控练习：暂停 Gazebo 后运行 pick.sh，观察就绪检查如何报错；恢复播放后重新检查。

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
bash cloudgrasp_sim/scripts/ready.sh --timeout 15
```

根据失败阶段区分：仿真/控制器未就绪、未识别到物体、规划失败、执行失败、物体未实际抓起。
日志位于 `/root/gpufree-data/cloudgrasp_ws/logs/`。
验收：独立完成一轮抓取，写一页总结，说明输入、识别、规划、控制和物理验证的关系。

## 每天的学习记录

在本目录新建 day01.md、day02.md 等，按以下模板记录：

```text
今天的目标：
执行过的命令：
观察到的现象：
我理解的原理：
遇到的问题和日志：
解决方法：
还不理解的地方：
```

完成上述阶段后，再学习 TF 标定、真实双目深度/点云接入、相机内外参、真实机械臂驱动和抓取姿态生成。
