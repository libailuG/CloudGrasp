# 第 1 天：操作 CloudGrasp 仿真

## 学习目标

亲自完成启动、抓取、重置和停止，并能解释各步骤的作用。
今天先练操作，不修改代码。所有命令在云服务器的终端执行。

## 操作步骤与解释

### 1. 进入项目并启动仿真

```bash
cd /root/gpufree-data/cloudgrasp_ws/src/CloudGrasp
pwd
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py start
```

- cd：切换终端当前目录。相对路径从这个目录开始查找。
- pwd：打印当前目录，确认进入了 CloudGrasp 项目。
- /usr/bin/python3：使用服务器的系统 Python，避免与其他 Python 环境混淆。
- manage.py start：启动 Gazebo、机器人、控制器、视觉感知、MoveIt 和 RViz，并检查是否就绪。已经运行时检查现有实例。
- 首次启动等待 Simulation ready；已经运行时等待 READY。
- Gazebo 展示物理仿真，包含运动、碰撞和物体接触；RViz 展示机器人状态和规划相关信息。
- 看到窗口不等于系统就绪，此时还没有发出抓取指令。

### 2. 执行一次抓取（确认第 1 步就绪后再做）

```bash
bash cloudgrasp_sim/scripts/pick.sh
```

bash 执行抓取入口脚本；脚本先检查系统状态，再运行视觉识别、运动规划与抓取，最后检查方块的真实仿真位移。
观察：张开夹爪 → 回初始姿态 → 识别 → 靠近 → 下降 → 夹紧 → 抬升 → 转移 → 放下 → 松开 → 撤离 → 回初始姿态。
看到 PHYSICAL_PICK_PLACE_PASS 才算整轮物理验证成功；仅有规划成功提示还不够。
运行期间不要重复启动抓取或重置方块。

### 3. 重置方块（抓取结束后）

```bash
bash cloudgrasp_sim/scripts/reset_cube.sh
```

把方块放回初始位置，方便下一次练习。它是场景重置操作，不是机械臂把方块搬回去。

### 4. 停止仿真（学习结束时）

```bash
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py stop
```

结束本项目管理的仿真进程。以后继续学习时重新执行第 1 步。

## 本次学习记录

- 已讲解：进入目录、启动命令及就绪提示的含义。
- 当前进度：第 1 天完成；操作练习与概念复盘均已通过。
- 学员实际操作结果：已执行启动命令，并反馈 READY 和 Simulation ready，确认启动成功。
- 后续记录：根据实际反馈补充，不将演示或历史运行当作本次完成。

## 完成标准

- [x] 能进入正确目录并确认仿真就绪。
- [x] 亲自运行抓取，观察动作并确认物理验证通过。
- [x] 抓取完成后重置方块。
- [x] 能停止仿真。
- [x] 能用自己的话解释 Gazebo 和 RViz 的区别。

### 第 1 步反馈：启动成功

学员反馈先出现 Waiting for，随后出现：

```text
READY: clock, joints, camera, controllers and actions are available.
Simulation ready. You can run pick.sh.
```

解释：启动过程中各模块陆续就绪，Waiting for 列出当时仍未满足的条件，并非最终失败。READY 表示仿真时钟正在推进、关节状态与相机点云在更新、控制器已激活、规划与感知动作服务可用。尚未发送抓取任务。

下一步：运行 bash cloudgrasp_sim/scripts/pick.sh，观察动作顺序并等待最终验证结果。抓取结果暂未确认。

### 第 2 步反馈：RViz 动，Gazebo 未动

学员观察 RViz 运动但 Gazebo 不动，日志停留在 Execute request accepted。后续日志显示轨迹成功，然而物理报告 physical_pass=false，方块高度始终约 0.025 m。本次抓取未通过。
检查发现旧 CloudGrasp Gazebo 服务进程（PID 171022）孤立存活，同时新实例运行。两者 Gazebo 分区不同，但 ROS 通信未隔离，可能造成控制与显示对应不同实例。已清理旧实例，并给管理脚本加入按工作空间路径和会话标记识别残留实例的清理。
知识点：Execute request accepted 仅表示请求被接受；必须继续观察执行结果和实际物体位移。修复后的自动验证属于教师排障验证，不能替代学员亲自完成练习。

### 修复后的排障验证

清理残留并重新启动后，自动抓取返回 PHYSICAL_PICK_PLACE_PASS：方块最高高度 0.204463 m，最终位置约 (0.449927, -0.249607, 0.025000) m。已重置方块供学员再次练习。
下一步由学员重新执行 pick.sh，观察 Gazebo 中方块抬升并反馈最终结果；本次自动验证不勾选学员抓取完成项。

### 如何清理后台并重新启动

在项目根目录逐条执行：

```bash
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py stop
/usr/bin/python3 cloudgrasp_sim/scripts/manage.py status
pgrep -af '[g]z sim.*cloudgrasp_sim'
```

stop 清理项目管理的仿真进程组；如果启动管理进程已退出，还会按本工作空间路径和会话标记寻找残留 Gazebo 服务。status 应显示 Stopped，但它主要检查管理进程，不能单独证明没有残留。最后一条用于补充检查：没有输出表示未匹配到本项目的 Gazebo 进程；有输出则保存结果进一步排查，不要盲目结束所有 Python 或 Gazebo 进程。

如果抓取脚本正在运行，先在运行 pick.sh 的终端按 Ctrl+C，等待其清理完成，再执行 stop。关闭终端窗口或只关闭图形窗口不等于完整停止仿真。

清理完成后运行 manage.py start，等 READY 再运行 pick.sh。日常只用管理脚本启动一套仿真，避免再手动运行 start.sh 或额外的 gz sim。

### 学员独立抓取：确认成功

学员明确反馈终端出现 PASS，并在 Gazebo 中看到机械臂将方块搬到另一处。结合终端验证与物理场景观察，确认本次独立抓取完成。
下一步：等待抓取脚本完全退出后执行 `bash cloudgrasp_sim/scripts/reset_cube.sh`，观察方块回到初始位置。该命令直接重置仿真物体位置，不是机械臂执行反向搬运。重置和停止步骤尚待学员反馈，不提前勾选。

### 学员重置方块：确认成功

学员反馈方块已回到原位，确认重置步骤完成。下一步由学员执行 manage.py stop、manage.py status，并用 pgrep 检查本项目 Gazebo 残留进程。停止结果尚待反馈。

### 学员停止仿真：确认成功

学员反馈 stop 输出 CloudGrasp stopped.，status 输出 Stopped，连续两次 pgrep 未显示匹配进程。确认停止与后台检查练习完成。
第 1 天操作部分全部完成：启动 → 抓取并确认 PASS 与物体移动 → 重置 → 停止并检查。概念验收尚待回答：Gazebo 与 RViz 各自的作用，以及为什么仅看到 RViz 运动不能判断抓取成功。

### 概念复盘：完成

学员回答：RViz 是状态和规划显示，Gazebo 中才是运行的机械臂。已理解可视化与物理仿真的关键区别。
补充：RViz 不仅显示规划轨迹，也可显示 /joint_states 等反馈数据、TF、点云；RViz 中运动不一定只是规划预览。Gazebo 中是物理仿真机械臂，并非真实硬件。抓取成功需要结合执行结果与仿真物体真实位移，本项目使用 PHYSICAL_PICK_PLACE_PASS 作最终验证。
第 1 天全部完成。下一课：ROS 2 节点与话题，先用 ros2 node list 和 ros2 topic list 查看运行中的系统。
