#!/usr/bin/python3
"""Tk controls -> FollowJointTrajectory actions -> measured JointState feedback.
No ROS thread touches Tk: the GUI timer spins ROS callbacks non-blockingly.
"""
import fcntl
import math
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import ttk
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from action_msgs.msg import GoalStatus

ARM=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
GRIP='robotiq_85_left_knuckle_joint'
HOME=[-1.57,-1.57,1.57,-1.57,-1.57,0.]
LABELS=['肩部旋转','肩部抬升','肘关节','手腕 1','手腕 2','手腕 3']

class Panel:
    def __init__(self,window):
        self.window=window;self.node=rclpy.create_node('lab_control_panel')
        self.actual={};self.limits={};self.feedback_time=0.;self.model_ready=False
        self.initialized=False;self.busy=False;self.handle=None;self.cancel_requested=False
        self.started=0.;self.duration=4.;self.closing=False;self.sent_names=[];self.sent_values=[]
        self.last_result=None;self.last_error=None;self.lock=None;self.target_vars=[];self.measured=[]
        self.clients={name:ActionClient(self.node,FollowJointTrajectory,f'/{name}_controller/follow_joint_trajectory') for name in ['arm','gripper']}
        self.node.create_subscription(JointState,'/joint_states',self.feedback,qos_profile_sensor_data)
        model_qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.node.create_subscription(String,'/robot_description',self.model,model_qos)
        self.build_ui();self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.after(50,self.tick)

    def build_ui(self):
        w=self.window;w.title('CloudGrasp · 机械臂控制面板');w.geometry('960x670');w.minsize(880,620)
        style=ttk.Style();style.theme_use('clam')
        style.configure('TFrame',background='#eef2f6');style.configure('TLabel',background='#eef2f6',font=('sans',11))
        style.configure('TButton',font=('sans',11),padding=8)
        frame=ttk.Frame(w,padding=22);frame.pack(fill='both',expand=True);frame.columnconfigure(2,weight=1)
        ttk.Label(frame,text='机械臂关节控制',font=('sans',20,'bold')).grid(row=0,column=0,columnspan=4,sticky='w')
        ttk.Label(frame,text='直接控制仿真关节，不经过 MoveIt 避障。先从手腕的小幅运动开始。').grid(row=1,column=0,columnspan=4,sticky='w',pady=(5,14))
        self.connection=tk.StringVar(value='正在连接 /joint_states、机器人模型和控制器…')
        ttk.Label(frame,textvariable=self.connection).grid(row=2,column=0,columnspan=4,sticky='w',pady=(0,12))
        for col,text in enumerate(['关节','实际角度','目标角度滑条','目标 / °']):
            ttk.Label(frame,text=text,font=('sans',10,'bold')).grid(row=3,column=col,sticky='w',padx=5)
        self.scales=[]
        for index,(joint,label) in enumerate(zip(ARM,LABELS)):
            row=4+index
            ttk.Label(frame,text=f'{label}\n{joint}',font=('sans',10)).grid(row=row,column=0,sticky='w',padx=5,pady=8)
            measured=tk.StringVar(value='等待反馈');self.measured.append(measured)
            ttk.Label(frame,textvariable=measured,width=15).grid(row=row,column=1,padx=8)
            value=tk.DoubleVar(value=0.);self.target_vars.append(value)
            scale=ttk.Scale(frame,from_=-180,to=180,variable=value,orient='horizontal',length=370)
            scale.grid(row=row,column=2,sticky='ew',padx=10);scale.state(['disabled'])
            scale.bind('<ButtonRelease-1>',self.on_release);self.scales.append(scale)
            number=tk.StringVar(value='0.0')
            value.trace_add('write',lambda *_,v=value,t=number:t.set(f'{v.get():.1f}'))
            ttk.Label(frame,textvariable=number,width=8).grid(row=row,column=3,padx=5)
        controls=ttk.Frame(frame);controls.grid(row=10,column=0,columnspan=4,sticky='ew',pady=(15,8))
        self.auto=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text='松开滑条自动执行',variable=self.auto).pack(side='left')
        ttk.Label(controls,text='   最短运动时间 / 秒').pack(side='left')
        self.seconds=tk.DoubleVar(value=4.)
        ttk.Spinbox(controls,from_=2,to=20,increment=1,textvariable=self.seconds,width=5).pack(side='left',padx=5)
        buttons=ttk.Frame(frame);buttons.grid(row=11,column=0,columnspan=4,sticky='ew',pady=5)
        self.motion_buttons=[]
        for title,callback in [('执行目标',self.send_arm),('目标跟随当前',self.sync_targets),('回初始姿态',self.home),('张开夹爪',lambda:self.send('gripper',[0.])),('完全闭合夹爪',lambda:self.send('gripper',[self.limits[GRIP][1]]))]:
            b=ttk.Button(buttons,text=title,command=callback);b.pack(side='left',padx=(0,6));self.motion_buttons.append(b)
        ttk.Button(frame,text='取消本面板运动',command=self.cancel).grid(row=12,column=0,columnspan=2,sticky='w',pady=8)
        self.gripper_state=tk.StringVar(value='夹爪：等待反馈')
        ttk.Label(frame,textvariable=self.gripper_state).grid(row=12,column=2,columnspan=2,sticky='w')
        self.status=tk.StringVar(value='未发送运动。模型和状态就绪后，滑条将初始化为当前关节位置。')
        ttk.Label(frame,textvariable=self.status,wraplength=900).grid(row=13,column=0,columnspan=4,sticky='w',pady=8)

    def model(self,msg):
        try:
            robot=ET.fromstring(msg.data)
            bounds={}
            for name in ARM+[GRIP]:
                joint=robot.find(f"joint[@name='{name}']");limit=joint.find('limit')
                bounds[name]=(float(limit.attrib['lower']),float(limit.attrib['upper']))
            self.limits=bounds;self.model_ready=True
            for name,scale in zip(ARM,self.scales):
                lo,hi=bounds[name];scale.configure(from_=math.degrees(lo),to=math.degrees(hi))
        except (ET.ParseError,AttributeError,KeyError,ValueError) as error:
            self.status.set('模型关节范围不可用：'+str(error));self.model_ready=False

    def feedback(self,msg):
        self.actual.update(zip(msg.name,msg.position));self.feedback_time=time.monotonic()

    def ready(self):
        return (self.model_ready and time.monotonic()-self.feedback_time<2
                and all(name in self.actual for name in ARM+[GRIP])
                and all(c.server_is_ready() for c in self.clients.values()))

    def sync_targets(self):
        if self.busy or not self.ready():return
        for name,var in zip(ARM,self.target_vars):var.set(math.degrees(self.actual[name]))
        self.status.set('目标已同步到当前反馈；没有发送运动。')

    def on_release(self,event=None):
        if self.auto.get() and not self.busy and self.initialized:self.send_arm()

    def send_arm(self):
        self.send('arm',[math.radians(v.get()) for v in self.target_vars])

    def home(self):
        if not self.ready() or self.busy:return
        for var,value in zip(self.target_vars,HOME):var.set(math.degrees(value))
        self.send('arm',HOME)

    def send(self,kind,values):
        if self.closing or self.busy:return
        if not self.ready():self.status.set('状态或控制器未就绪：请确认阶段 2 运行且 Gazebo 未暂停。');return
        names=ARM if kind=='arm' else [GRIP]
        if len(values)!=len(names) or any(not math.isfinite(v) or not self.limits[k][0]<=v<=self.limits[k][1] for k,v in zip(names,values)):
            self.status.set('目标超出机器人模型的关节限制。');return
        try:
            requested=float(self.seconds.get())
            if not math.isfinite(requested) or not 2<=requested<=20:raise ValueError()
        except (ValueError,tk.TclError):self.status.set('运动时间应为 2～20 秒。');return
        path=Path(__file__).resolve().parents[2]/'.runtime/action.lock'
        path.parent.mkdir(exist_ok=True)
        lock=path.open('w')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:lock.close();self.status.set('其他实验命令正在执行，请等待完成。');return
        self.lock=lock
        # Increase time for large angle changes instead of traversing the entire range in two seconds.
        delta=max(abs(v-self.actual[k]) for k,v in zip(names,values))
        self.duration=max(requested,delta/.25)
        goal=FollowJointTrajectory.Goal();goal.trajectory.joint_names=names
        point=JointTrajectoryPoint();point.positions=list(values)
        point.time_from_start.sec=int(self.duration)
        point.time_from_start.nanosec=int((self.duration-int(self.duration))*1e9)
        goal.trajectory.points=[point]
        self.busy=True;self.cancel_requested=False;self.handle=None
        self.started=time.monotonic();self.sent_names=list(names);self.sent_values=list(values)
        self.last_result=None;self.last_error=None
        self.status.set(f'正在发送 {kind} 目标，轨迹时长约 {self.duration:.1f} 秒…')
        self.clients[kind].send_goal_async(goal).add_done_callback(self.accepted)

    def accepted(self,future):
        try:
            self.handle=future.result()
            if not self.handle.accepted:self.finish('控制器拒绝目标。',error='rejected');return
            self.status.set('控制器已接受目标，等待实际执行结果…')
            self.handle.get_result_async().add_done_callback(self.result)
            if self.cancel_requested or self.closing:self.send_cancel()
        except Exception as error:self.finish('发送失败：'+str(error),error=str(error))

    def result(self,future):
        try:
            result=future.result()
            if result.status==GoalStatus.STATUS_CANCELED:
                self.finish('本面板的运动已取消。',error='canceled');return
            if result.status!=GoalStatus.STATUS_SUCCEEDED or result.result.error_code!=0:
                self.finish('执行失败：'+result.result.error_string,error=result.result.error_string or str(result.status));return
            # Wait for a subsequent feedback message before declaring measured success.
            self.verify_after=time.monotonic();self.verify_deadline=self.verify_after+3
            self.status.set('轨迹结束，正在核对实际关节反馈…')
        except Exception as error:self.finish('结果读取失败：'+str(error),error=str(error))

    def finish(self,message,error=None):
        self.status.set(message);self.last_error=error;self.last_result=(error is None)
        self.busy=False;self.handle=None
        if hasattr(self,'verify_after'):del self.verify_after
        if self.lock is not None:self.lock.close();self.lock=None

    def cancel(self):
        if not self.busy:self.status.set('本面板当前没有正在执行的运动。');return
        if not self.cancel_requested:
            self.cancel_requested=True;self.status.set('正在请求取消；等待控制器确认…')
            if self.handle is not None:self.send_cancel()

    def send_cancel(self):
        self.handle.cancel_goal_async().add_done_callback(self.cancel_reply)

    def cancel_reply(self,future):
        try:
            if not future.result().goals_canceling and self.busy:
                self.status.set('控制器未确认取消，继续等待执行结果。')
        except Exception as error:self.status.set('取消请求异常：'+str(error))

    def tick(self):
        if not rclpy.ok():return
        rclpy.spin_once(self.node,timeout_sec=0)
        ready=self.ready()
        self.connection.set('● 已连接：关节反馈、模型和两个轨迹控制器' if ready else '○ 未就绪：请启动阶段 2，并保持仿真播放')
        if ready and not self.initialized:self.sync_targets();self.initialized=True
        for name,var in zip(ARM,self.measured):
            if name in self.actual:var.set(f'{math.degrees(self.actual[name]):.1f}° / {self.actual[name]:.3f} rad')
        if GRIP in self.actual:self.gripper_state.set(f'夹爪实际关节：{self.actual[GRIP]:.3f} rad（不是夹持力）')
        for widget in self.scales+self.motion_buttons:
            widget.state(['!disabled'] if ready and not self.busy and not self.closing else ['disabled'])
        if self.busy and hasattr(self,'verify_after'):
            if self.feedback_time>self.verify_after:
                error=max(abs(self.actual[k]-v) for k,v in zip(self.sent_names,self.sent_values))
                self.finish(f'完成：实际关节反馈已核对，最大误差 {error:.4f} rad。' if error<=.01 else f'反馈未到达目标，最大误差 {error:.4f} rad。',error=None if error<=.01 else 'position error')
            elif time.monotonic()>self.verify_deadline:self.finish('缺少执行后的新鲜反馈，不能确认到位。',error='feedback timeout')
        if self.busy and not self.cancel_requested and (time.monotonic()-self.started>self.duration+15 or time.monotonic()-self.feedback_time>3):self.cancel()
        if self.closing and not self.busy:
            self.shutdown();return
        self.window.after(50,self.tick)

    def close(self):
        self.closing=True
        if self.busy:self.cancel()
        else:self.shutdown()

    def shutdown(self):
        for client in self.clients.values():client.destroy()
        self.node.destroy_node();self.window.destroy()


def main():
    rclpy.init();window=tk.Tk();panel=Panel(window)
    try:window.mainloop()
    finally:
        if rclpy.ok():rclpy.shutdown()

if __name__=='__main__':main()
