# 代码验证记录

本文件记录编写参考代码时的验证，不代表学员已完成对应关卡。学员进度单独保存在 notes/。
环境：Ubuntu 24.04、ROS 2 Jazzy、Gazebo Harmonic、MoveIt 2；实验 ROS_DOMAIN_ID=42。

## 已完成

- cloudgrasp_lab 编译成功，包含 lab_motion 与 lab_task 两个 C++ 可执行程序。
- Python 语法检查、Bash 语法检查、git diff --check 通过。
- 阶段 1 独立启动就绪；控制器列表只有激活的 joint_state_broadcaster。退出输出 LAB_STOPPED。
- 阶段 3 独立启动，覆盖机械臂轨迹控制器和相机功能：wrist、home、close、open 均返回 JOINT_OK。
- 相机观察：320×240 RGB 图像；点云 camera_link，320×240，字段 x/y/z/rgb。
- 阶段 7 带 GUI/RViz 的完整节点图启动就绪；覆盖阶段 4～6 所需模块。
- 视觉检测发现 2 个候选、1 个支撑面，目标方块位置约 (0.45,0.149498,0.025) 米。
- 正常目标规划返回 PLAN_OK、PLAN_ONLY；计划命令退出码 0。
- 障碍物同时加入 Gazebo 和 MoveIt，场景查询包含 lab_obstacle 和 table。
- 阻挡目标的障碍物使 IK 返回 No collision-free IK solution，命令退出码 1，没有执行目标轨迹；移除后可正常规划。
- 末端目标实际执行与回 home 均返回 EXECUTION_OK，命令退出码 0。
- 独立 lab_task 完整抓取返回 PHYSICAL_PICK_PLACE_PASS；方块最高 Z=0.2044526104 米，最终位置 (0.4499499126,-0.2495413647,0.0249999458) 米。
- 物理报告：.runtime/pick-20260906-165517.json。

## 测试中修复的问题

1. ros_gz_sim create 从文件生成相机时覆盖初始位姿：改为从相机 SDF 读取 pose，并显式传入创建参数；同一 pose 生成静态 TF。
2. MoveItConfigsBuilder 自动加载未提供的 Pilz 配置：明确只使用 OMPL。
3. 此模型的直接位姿目标采样未找到轨迹：改为显式、基于当前关节状态的碰撞检查 IK，归一化等价转角后规划关节目标。
4. ros2 launch 的退出码可能掩盖节点异常：motion_run.py 检查 PLAN_OK/EXECUTION_OK 标记并返回失败状态。

## 验证边界

- 阶段 2、4、5、6 的单独启动参数未逐个重复启动；它们的功能在阶段 3/7 节点图中分别执行验证。修改阶段条件后需要重新检查。
- 不声称已验证所有目标、速度、相机位置或障碍布局；每次学员改动仍需按关卡重新验证。
- GUI/RViz 进程已启动，障碍物添加和规划通过接口验证；屏幕显示效果由学员在桌面观察。
- 阶段 7 源码从已验证的原抓取器改编，明确作为可运行的完整对照，不是全新算法。

最终复核：Gazebo 中 lab_obstacle 位姿为 (0.60,-0.25,0.15) 米，与 MoveIt 配置一致。移除障碍后再次规划退出码 0；方块已复位，测试仿真正常停止并输出 LAB_STOPPED。
