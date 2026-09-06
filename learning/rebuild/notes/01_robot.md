# 关卡 1：加载机械臂

状态：代码已准备，等待学员亲自运行。

- 阅读文件：launch/lab.launch.py、worlds/01_table.sdf。
- 我的理解：
- 启动命令与输出：
- Gazebo 中看到的内容：
- /joint_states 输出：
- 控制器列表：
- 自己做的修改与结果：
- 遇到的问题：

验收：看见模型、收到关节反馈、知道模型发布与实体生成的区别。

## 基础 RViz 补充

第 1～3 阶段现默认启动基础 RViz RobotModel；第 4 阶段起使用 MoveIt 视图。配置为 cloudgrasp_lab/config/robot.rviz。已验证构建、stage=1/4 的 rviz 参数分支、模型话题订阅和重启后 world→grasp_tcp TF。原先第一阶段进程在检查中退出，随后已用新入口重新启动第一阶段；Gazebo/RViz 统一由 lab.sh 管理。

## RViz Orbit 无法拖动修复

学员确认 Orbit 模式仍无法拖动。检查保存后的配置发现 Tools 为空：缺少 MoveCamera 等鼠标工具。已补充 MoveCamera（列表首项）、Interact、Select、FocusCamera、Measure，并保留用户已保存的显示及视角设置；同时补齐后续阶段使用的 demo.rviz 工具。
