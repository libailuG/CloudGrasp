# 第 6 课：修改参数、构建与验证

## 本次实验

只把 vision_pick_place.cpp 中预抓取 Z 偏移从 0.18 米改成 0.22 米。观察到达方块上方的高度变化，同时检查整轮物理抓取是否通过。这只是本仿真练习的候选参数，是否规划和执行成功以测试为准。
不改变 approach、lift、transfer、lower、retreat 参数，不全局替换 0.18。

## 修改前检查

已检查服务器当前 git status：build.sh、VS Code 配置和学习记录有已有改动；vision_pick_place.cpp 无未提交改动。不得清理其他现有改动。
当前目标语句位于 pregrasp from vision 之前：pose.position=position; pose.position.z+=0.18;
学员应在 VS Code 手动修改该处 0.18 为 0.22，保存后查看：

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
git diff -- cloudgrasp_sim/src/vision_pick_place.cpp
```

预期仅预抓取的 0.18→0.22 改变。物体中心 z=0.025 米时，末端预抓取目标 z 从 0.205 米变成 0.245 米，增加 4 厘米。后续 approach 仍指定 z=position.z+0.008，因此最终接近高度不变。

## 后续步骤

1. 检查学员差异，确认只修改目标位置。
2. 学员构建 cloudgrasp_sim 包；源码保存不等于已运行新二进制，symlink-install 不免除 C++ 编译。
3. 构建成功后启动或重启仿真，等待 READY，重置方块并执行抓取。
4. 观察预抓取高度与最终 PHYSICAL_PICK_PLACE_PASS，记录成功或失败，失败时按日志排查。
5. 说明物体抬升峰值不必因此增加 4 厘米，因为夹紧后的 lift 偏移没有修改。

## 验收与记录

- 当前阶段：第 6 课完成；源码修改、构建、运行验证与影响分析全部通过。
- [x] 修改范围正确。
- [x] 构建成功。
- [x] 观察预抓取变化并记录物理验证结果。
- [x] 解释修改影响了哪些阶段。

## 源码修改检查：通过

学员提供 git diff，确认只改 pregrasp 前的 pose.position.z+=0.18 为 +=0.22，其他阶段不变。下一步使用系统 ROS 环境，在工作空间根目录执行 colcon build --symlink-install --packages-select cloudgrasp_sim --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON。保存源代码不会自动更新 C++ 可执行程序，symlink-install 也不能替代编译。构建结果尚待反馈，不提前勾选。

## 构建结果：通过

学员反馈 cloudgrasp_sim 构建成功：Finished [11.5s]，Summary: 1 package finished [11.7s]。
下一步确认没有抓取正在执行，再 stop/start 仿真，等 READY 后重置方块并执行 pick.sh。此次重启用于统一实验初始状态；单独更新抓取 C++ 程序后，新启动的抓取进程才使用新程序，已运行的抓取进程不会自动替换。
观察重点为 pregrasp 阶段 TCP 高度从约 0.205 米升到 0.245 米；approach 最终高度与夹持后 lift 偏移不变。记录用户所见及最终 PASS/FAIL，不能只凭构建成功判定行为正确。

## 修改后实验：通过

学员确认看到了预抓取位置变高，并提供 PHYSICAL_PICK_PLACE_PASS。
- 方块最高中心高度：0.20483883279780069 米。
- 最终位置：(0.4499156834430654,-0.2500620623676582,0.024999872897600642) 米。
- 报告：/root/gpufree-data/cloudgrasp_ws/logs/pick-20260906-155825.json。

解释：预抓取目标 TCP Z 约 0.245 米，但 Peak height 统计的是 Gazebo 方块中心的最高高度，两者不是同一个测量对象。夹爪在预抓取位置时尚未夹住方块，后续 approach 把目标 Z 设回物体中心 Z+0.008；夹持后的 lift 偏移仍为 0.18 米。因此方块峰值不应因本次改动被假定增加 4 厘米。
当前阶段：修改、构建和实验验证通过；最后等待学员解释 pregrasp 与物体抬升峰值的区别。

## 第 6 课最终复盘：完成

学员正确指出只提高了预抓取目标 4 厘米，后续下降、抓取和抬升参数未变。补充：下降终点不变，但下降起点提高，因此 approach 的竖直路程增加 4 厘米，轨迹与耗时可能变化；不能笼统说下降过程完全不受影响。夹持后的 lift 偏移不变，所以方块最高高度不会必然随预抓取提高而增加。
第 6 课全部验收完成。当前源码保留学员实验的预抓取偏移 0.22 米，未恢复为 0.18，也未代替学员提交此修改。下一课按计划学习故障排查与复盘。
