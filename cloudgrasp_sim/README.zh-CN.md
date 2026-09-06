# CloudGrasp 云服务器仿真（ROS 2 Jazzy）

此扩展在原 CloudGrasp 点云感知代码上补齐了可运行的 Gazebo Harmonic 仿真：UR5、Robotiq 2F-85、桌面、方块、RGB-D 相机、ros2_control、MoveIt 2 和抓取执行程序。

## 环境与边界

- Ubuntu 24.04 + ROS 2 Jazzy；保留服务器现有 ROS，不安装 Humble。
- Gazebo Harmonic / gz-sim 8，UR5 与 Robotiq 使用 ROS 官方发行的描述包。
- 仿真相机生成 RGB、深度和点云；这里**没有仿真双目视差匹配**。真实双目相机的驱动、标定和硬件抓取还需单独接入。
- 抓取目标由点云分割识别；Gazebo 物体真值只用于结果验证，不参与抓取定位。
- Gazebo 中物体依靠夹爪接触/摩擦运动；MoveIt 的 attached collision object 只用于携带物体的碰撞规划，不会在 Gazebo 中吸附或搬动物体。
- 当前验证对象为桌面上的约 40 × 40 × 50 mm 方块，放置区 y=-0.25 m。它不是任意物体或杂乱场景抓取系统。

## 本服务器目录

工作空间：`/root/gpufree-data/cloudgrasp_ws`

仓库：`/root/gpufree-data/cloudgrasp_ws/src/CloudGrasp`

日志与物体轨迹：工作空间的 `logs/` 目录。

## 云桌面使用

1. 点击 **CloudGrasp - Start Simulation**，等待终端输出 `Simulation ready. You can run pick.sh.`。仅出现窗口不代表控制器已就绪。
2. 点击 **CloudGrasp - Run Pick and Place**。
3. 成功时终端输出 `PHYSICAL_PICK_PLACE_PASS`，对应 JSON 保存最高抬升高度、最终位置及采样轨迹。
4. 再次演示前点击 **CloudGrasp - Reset Cube**。也可以在 Gazebo 中移动方块，验证相机重新定位。
5. 点击 **CloudGrasp - Stop Simulation** 关闭本工作空间启动的仿真进程。

请先等当前抓取结束再停止仿真。抓取和重置之间有互斥锁，重复点击不会同时启动多个抓取。

## 命令行

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py start
bash cloudgrasp_sim/scripts/pick.sh
bash cloudgrasp_sim/scripts/reset_cube.sh
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py stop
```

服务器预装 Isaac Sim 的 `python3` 可能指向 Python 3.11，ROS Jazzy 使用系统 Python 3.12。运行 ROS Python 工具时使用 `/usr/bin/python3`，避免 ABI 不兼容。

## 在相同系统上重新构建

前提：Ubuntu 24.04 已配置 ROS 2 软件源。

```bash
mkdir -p ~/cloudgrasp_ws/src
cd ~/cloudgrasp_ws/src
git clone https://github.com/libailuG/CloudGrasp.git
# 切换到包含本扩展的分支/提交；未推送时先应用提供的源码补丁。
cd CloudGrasp
bash cloudgrasp_sim/scripts/install_dependencies.sh
bash cloudgrasp_sim/scripts/build.sh
```

`start.sh` 默认连接本云桌面 `DISPLAY=:20`；其他环境通过 `DISPLAY` 环境变量覆盖。无 GUI 时可使用 `start.sh gui:=false rviz:=false`，RGB-D 渲染仍需可用的图形环境。

## 实现要点

- 修正 Gazebo 点云的相机坐标定义；感知距离过滤轴可通过 `range_field_name` 配置。Gazebo 使用 x 向前，常见 RealSense optical frame 使用 z 向前。
- 感知订阅使用 Best Effort QoS，可兼容传感器数据发布。
- 待机姿态避开相机视野；抓取位置来自 `find_objects`，高度来自物体形状估计。
- 明确设置归一化的朝下四元数，避免默认 w 分量引入 90 度姿态错误。
- 碰撞感知 IK、等价关节角择近、有限重试；规划失败或笛卡尔路径不完整时停止执行。
- 桌面和携带物体进入 MoveIt 碰撞场景；夹爪接触行为在 Gazebo 中独立仿真。
- `watch_cube.py` 独立记录真值轨迹。完整机械臂动作成功后，还要求抬升超过 8 cm、落点进入 3 cm 平面容差并回到桌面高度，才输出物理成功。

## 真实双目相机后续接入

接入真实相机时，需要用其 ROS 2 驱动发布 `sensor_msgs/PointCloud2`，正确配置相机到机械臂基座的 TF，以及 `frame_id`、`range_field_name` 和工作空间过滤范围。不能直接用本仿真的固定相机外参控制真实机器人。本扩展只启动仿真控制器。

## 不动、暂停或启动失败时

先检查就绪状态：

```bash
bash cloudgrasp_sim/scripts/ready.sh --timeout 15
```

脚本检查仿真时钟是否递增、关节状态与点云是否新鲜、三个控制器是否激活，以及 MoveIt/感知动作服务是否可用。Gazebo 暂停时，请在其窗口恢复播放。其他启动问题可先停止，再启动：

```bash
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py stop
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py start
```

`pick.sh` 现在自动执行上述检查，未就绪时在 15 秒内退出，不会进入无限等待。运行阶段还有 240 秒的墙钟超时；中断或失败时清理本次 ROS 子进程，避免遗留抓取锁。

每次启动使用独立的 Gazebo 通信会话。如果需要自己执行 `gz` 调试命令，先运行：

```bash
source /root/gpufree-data/cloudgrasp_ws/logs/session.env
```

相机/关节等 ROS 话题名称保持不变。
