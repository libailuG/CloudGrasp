# CloudGrasp 学习阶段结项

2026-09-06，学员确认本项目本轮学习结束。

已实践 ROS 2 节点与话题、关节状态、Launch、Gazebo 与 RViz、控制器、视觉检测、MoveIt 规划执行和物理抓取验证；已修改预抓取高度并观察结果，使用分阶段实验和控制面板控制关节，并确认夹爪完全闭合修正有效。

完整实验代码与逐阶段说明见 rebuild/README.md；控制面板说明见 rebuild/CONTROL_PANEL.md。各阶段的助手验证与学员记录仍以原记录为准；结项不表示所有扩展练习都由学员独立完成。

## 下一项目建议：MoveIt Task Constructor

开源仓库：https://github.com/moveit/moveit_task_constructor

目标：在现有基础上学习分阶段任务规划、多候选抓取姿态、障碍物约束和失败分析。

1. 运行官方抓放示例，在 RViz 观察任务各阶段与候选解。
2. 从代码构造 CurrentState、MoveTo、MoveRelative 等简单阶段。
3. 增加 GenerateGraspPose 与 ComputeIK，观察候选解的筛选。
4. 加入障碍物，检查失败阶段和规划场景的影响。
5. 适配现有 UR5 与 Robotiq，再接入点云检测结果。
6. 接入 Gazebo 实际执行并验证方块的物理位移。

沿用当前 ROS 2 Jazzy；实施前核对 MTC 与已安装 MoveIt 的版本兼容性。官方规划示例的成功不能替代 Gazebo 物理抓取验证。
