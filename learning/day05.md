# 第 5 课：从视觉位置到机械臂动作

## 目标

读懂 vision_pick_place.cpp 中预抓取、接近、夹紧、抬升、转移和释放的过程，区分目标位姿、逆运动学、规划和执行。
本课先只读，不修改参数或运行抓取。

## 第 1 步：预抓取位置

打开 cloudgrasp_sim/src/vision_pick_place.cpp，搜索 pregrasp from vision。
代码先读取 target.primitive_poses[0].position，再将它赋给末端目标 pose.position，并增加 z=0.18 米。

```cpp
auto position = target.primitive_poses[0].position;
geometry_msgs::msg::Pose pose;
pose.orientation.y = 1.0;
pose.orientation.w = 0.0;
pose.position = position;
pose.position.z += 0.18;
set_target(arm, node, pose);
execute(arm, logger, "pregrasp from vision");
```

目标参考系通过 setPoseReferenceFrame("world") 设置，受控末端为 setEndEffectorLink("grasp_tcp")。因此 pose 是 grasp_tcp 的目标位姿，不是修改方块的位姿。它也不是六个关节角；后续需要逆运动学与规划。
物体中心 z=0.025 米时，预抓取末端 z=0.205 米，表示高于物体中心 18 厘米；不是高于顶面 18 厘米。先到上方，再沿接近方向下降，有利于把接近过程单独规划和检查；不能仅凭抬高就保证无碰撞。
orientation 的 x/y/z/w 是四元数分量，不是 roll/pitch/yaw；本课稍后解释，当前先关注位置。

## 进度

- 当前步骤：学员查看预抓取代码并计算末端目标位置。
- [x] 区分物体位置与末端目标位姿。
- [x] 理解逆运动学的输入与输出。
- [x] 区分规划与执行。
- [x] 理解接近和抬升的笛卡尔路径。
- [x] 串联抓取各阶段并解释物理验证的作用。

口头练习：物体位置为 (0.45,0.15,0.025) 米时，增加 z=0.18 后，预抓取末端的 XYZ 是多少？等待回答。

## 预抓取位置复盘：通过

学员正确回答 X/Y 不变、Z=0.205 米。下一步查看 set_target 函数中的 /compute_ik 服务，学习逆运动学：给定末端目标位置和姿态、机器人模型以及当前关节状态作为求解参考，寻找满足目标的关节配置。逆运动学不等于规划完整轨迹，也不直接执行运动；目标可能无解或存在多解。具体配置以当前源码为准。

## 逆运动学复盘：通过

学员正确回答 IK 成功只是计算，没有使机械臂运动到目标。下一步阅读项目 execute() 辅助函数，区分 arm.plan(plan) 计算轨迹与 arm.execute(plan) 执行已规划轨迹。IK 目标配置无碰撞不保证从当前状态到目标的整条路径无碰撞或一定可达，仍需规划与执行检查。

## 规划与执行复盘：通过

学员正确回答：只规划而不执行不会引起这次目标运动，因为没有下发执行请求。
下一步阅读 approach 的 cartesian() 调用：pose.position.z=position.z+0.008。物体中心 z=0.025 米时接近目标 TCP z=0.033 米；这是本夹爪 TCP 和场景配合使用的参数，不是任意机械臂的通用安全高度。
cartesian() 中 computeCartesianPath({pose},0.005,trajectory) 尝试从当前末端位姿沿直线位置插值到目标，0.005 为末端平移插值的最大步长（米），不是速度或关节角。此处目标朝向保持不变、X/Y 不变，因此意图是竖直下降。fraction 表示路径计算完成比例，不是实际运动进度。程序要求 fraction>0.999，否则报错，不执行不完整路径。直线接近不等于遇到障碍时自动绕行。
下一问：fraction=0.6 表示路径仅算出约 60% 时，当前代码会继续执行还是报错停止该流程？等待回答。

## 笛卡尔路径完整性复盘：通过

学员正确回答 fraction=0.6 时不会执行不完整轨迹，会报错结束当前流程。
下一步阅读 close gripper 及 AttachedCollisionObject：夹爪关节目标 0.48 为本模型驱动转动关节的角度（弧度），不是张开宽度或夹持力；execute 完成后，程序向 MoveIt 规划场景添加附着碰撞物体，使规划考虑被搬运物体的体积。该操作不在 Gazebo 中创建物理固定连接，不保证实际抓住；Gazebo 的物体运动依赖夹爪接触等物理作用，后续 watch_cube 的物体位移检查才验证抓取结果。
提问：如果 MoveIt 已添加附着物体，但 Gazebo 中夹爪没有夹住方块，方块会因为此操作自动跟着夹爪走吗？等待回答。

## 附着物体与物理夹持复盘：通过

学员正确指出 MoveIt 附着物体不能让未夹住的 Gazebo 方块自动随动。补充：这里的附着操作用于更新规划场景中的随动物体与碰撞关系；MoveIt 整体还负责运动学、规划和执行协调，不应概括为仅关心碰撞尺寸。

后半段流程：lift 将接近位姿的 Z 增加 0.18 米；transfer 保持当前 X/Z，将 Y 设为 -0.25 米，求 IK 后规划并执行；lower 将 Z 设为检测物体中心 Z+0.012；release 张开夹爪；从规划场景移除附着关系和对象；retreat 抬高 0.18 米；return home 返回初始姿态。
注意 pose.position.y=-0.25 是设置世界 Y 目标，不是沿 Y 移动 -0.25 米；若起始 Y=0.15 米，变化量为 -0.40 米。本处描述的是末端目标，实际轨迹与物体位移需执行后验证。
下一问：从 Y=0.15 米到 Y=-0.25 米，末端目标的 Y 变化量为多少米？等待回答。

## 放置坐标复盘

学员回答 Y 移动 0.4 米，并询问为何设为 -0.25。已区分距离 0.4 米与有符号变化量 -0.4 米。-0.25 是本演示人为指定的放置世界 Y 坐标，不是视觉测量或 IK 自动选择的放置位置；抓取位置来自视觉，放置目标由任务指定，路径由规划求解。

## 实际物体位移验证

下一步阅读 scripts/watch_cube.py 与 scripts/run_pick.py。watch_cube 采样 Gazebo 方块位姿，保存 initial、final、max_height；lifted 要求最大 Z 大于初始 Z+0.08 米。run_pick 在运动流程正常完成后还检查：已抬起；最终 Y 距 -0.25 米小于 0.03 米；最终 X 距初始 X 小于 0.03 米；最终 Z 距 0.025 米小于 0.015 米。全部满足才输出 PHYSICAL_PICK_PLACE_PASS。
这些条件验证本演示的采样位移，不等于验证任意真实机械臂抓取安全性，也不直接测量夹持力。物理观测不作为视觉定位来源。
口头练习：如果运动脚本完成，但方块始终留在初始位置，是否会得到 PHYSICAL_PICK_PLACE_PASS？指出至少一个不满足的条件。等待回答。

## 物理验证复盘：通过

学员正确回答方块始终原地时不会 PASS，因为抬升和放置位置条件不满足。第 5 课全部验收完成。

## 追问：watch_cube.py 如何读取方块位置

已核对源码：使用 subprocess.Popen 运行 gz topic -e -t /world/cloudgrasp/dynamic_pose/info，读取 Gazebo Transport 的动态位姿消息文本；不是读取 /camera/points，也不是视觉识别。按 name: "target_cube" 找到模型，再解析其 position 中的 x/y/z。该世界中的顶层 target_cube 模型位置用来作仿真真值验证。
脚本使用 time.monotonic 计算经过的墙钟时间，间隔至少 0.1 秒保存一次样本，即保存频率最多约 10 Hz，不等于话题本身发布频率。最后计算 initial、final、max_height 和 lifted，并写 JSON。模型名来自 tabletop.sdf；如果改模型名，监视脚本也需对应修改。独立运行 gz 查看命令前须 source 工作空间 logs/session.env，使 GZ_PARTITION 与当前仿真实例一致。
该真值只用于验收，抓取目标定位仍来自点云；仅用于仿真的评价通道不能直接当作真实机械臂的传感器。

## 真值验证边界复盘

学员准确指出 watch_cube.py 是仿真上帝视角，并非传感器测量。已明确区分：视觉点云用于抓取定位，Gazebo 真值仅用于结果验收；真实系统需要独立传感与验证方案。
