#include <chrono>
#include <cmath>
#include <future>
#include <map>
#include <moveit_msgs/srv/get_position_ik.hpp>
#include <moveit/robot_state/conversions.hpp>
#include <memory>
#include <stdexcept>
#include <thread>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <grasping_msgs/action/find_graspable_objects.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
#include <moveit/planning_scene_interface/planning_scene_interface.hpp>
using namespace std::chrono_literals;
using MoveGroup = moveit::planning_interface::MoveGroupInterface;
using Find = grasping_msgs::action::FindGraspableObjects;
void require(bool ok, const std::string& message) { if (!ok) throw std::runtime_error(message); }
void execute(MoveGroup& group, const rclcpp::Logger& log, const std::string& stage) {
  RCLCPP_INFO(log, "STAGE: %s", stage.c_str());
  group.setStartStateToCurrentState();
  MoveGroup::Plan plan;
  bool planned=false;
  for(int attempt=0; attempt<3 && !planned; ++attempt) planned=group.plan(plan)==moveit::core::MoveItErrorCode::SUCCESS;
  require(planned, stage+": planning failed after 3 attempts");
  require(group.execute(plan)==moveit::core::MoveItErrorCode::SUCCESS,stage+": execution failed");
}
void cartesian(MoveGroup& arm, geometry_msgs::msg::Pose pose, const rclcpp::Logger& log, const std::string& stage) {
  RCLCPP_INFO(log,"STAGE: %s",stage.c_str());
  arm.setStartStateToCurrentState();
  moveit_msgs::msg::RobotTrajectory trajectory;
  double fraction=arm.computeCartesianPath({pose},0.005,trajectory);
  require(fraction>0.999,stage+": incomplete Cartesian path ("+std::to_string(fraction)+")");
  require(arm.execute(trajectory)==moveit::core::MoveItErrorCode::SUCCESS,stage+": execution failed");
}
void set_target(MoveGroup& arm,const rclcpp::Node::SharedPtr& node,const geometry_msgs::msg::Pose& pose) {
  auto client=node->create_client<moveit_msgs::srv::GetPositionIK>("/compute_ik");
  require(client->wait_for_service(5s),"IK service unavailable");
  auto request=std::make_shared<moveit_msgs::srv::GetPositionIK::Request>();
  request->ik_request.group_name="ur_manipulator";
  request->ik_request.ik_link_name="grasp_tcp";
  request->ik_request.avoid_collisions=true;
  request->ik_request.pose_stamped.header.frame_id="world";
  request->ik_request.pose_stamped.pose=pose;
  request->ik_request.timeout.sec=3;
  auto state=arm.getCurrentState(5);require(bool(state),"No state for IK seed");
  moveit::core::robotStateToRobotStateMsg(*state,request->ik_request.robot_state);
  auto future=client->async_send_request(request);
  require(future.wait_for(8s)==std::future_status::ready,"IK timeout");
  auto response=future.get();require(response->error_code.val==1,"No collision-free IK solution");
  auto seed=*state;
  moveit::core::robotStateMsgToRobotState(response->solution,*state);
  for(const auto* joint:state->getJointModelGroup("ur_manipulator")->getActiveJointModels()) {
    const auto& name=joint->getVariableNames().front();
    const auto& bounds=state->getRobotModel()->getVariableBounds(name);
    double value=state->getVariablePosition(name),best=value,reference=seed.getVariablePosition(name);
    for(int turn=-2;turn<=2;++turn) {
      double candidate=value+turn*2.0*3.141592653589793;
      if(bounds.position_bounded_&&(candidate<bounds.min_position_||candidate>bounds.max_position_))continue;
      if(std::abs(candidate-reference)<std::abs(best-reference))best=candidate;
    }
    state->setVariablePosition(name,best);
  }
  arm.setJointValueTarget(*state);
}
int main(int argc,char** argv) {
  rclcpp::init(argc,argv);
  rclcpp::NodeOptions options; options.automatically_declare_parameters_from_overrides(true);
  auto node=rclcpp::Node::make_shared("cloudgrasp_pick",options);
  auto logger=node->get_logger();
  rclcpp::executors::MultiThreadedExecutor executor; executor.add_node(node);
  std::thread spin([&]{executor.spin();}); int code=0;
  try {
    MoveGroup arm(node,"ur_manipulator"),gripper(node,"gripper");
    arm.setPoseReferenceFrame("world"); arm.setEndEffectorLink("grasp_tcp");
    arm.setPlanningTime(15.0); arm.setNumPlanningAttempts(10);
    arm.setMaxVelocityScalingFactor(0.2); arm.setMaxAccelerationScalingFactor(0.2);
    gripper.setMaxVelocityScalingFactor(0.3); gripper.setMaxAccelerationScalingFactor(0.3);
    moveit::planning_interface::PlanningSceneInterface scene;
    moveit_msgs::msg::CollisionObject table; table.id="table"; table.header.frame_id="world";
    shape_msgs::msg::SolidPrimitive box; box.type=box.BOX; box.dimensions={1.7,1.5,0.07};
    geometry_msgs::msg::Pose table_pose; table_pose.orientation.w=1; table_pose.position.x=0.25; table_pose.position.z=-0.035;
    table.primitives={box}; table.primitive_poses={table_pose}; table.operation=table.ADD;
    require(scene.applyCollisionObject(table),"Could not add table to planning scene");
    require(bool(arm.getCurrentState(15)),"No current arm state");
    gripper.setNamedTarget("gripper_open"); execute(gripper,logger,"open gripper");
    arm.setNamedTarget("home"); execute(arm,logger,"move home");
    auto client=rclcpp_action::create_client<Find>(node,"find_objects");
    require(client->wait_for_action_server(15s),"Perception action unavailable");
    Find::Goal goal; goal.plan_grasps=false;
    auto future=client->async_send_goal(goal);
    require(future.wait_for(15s)==std::future_status::ready,"Perception goal timeout");
    auto handle=future.get(); require(bool(handle),"Perception rejected goal");
    auto result_future=client->async_get_result(handle);
    require(result_future.wait_for(30s)==std::future_status::ready,"Perception result timeout");
    auto result=result_future.get(); require(result.code==rclcpp_action::ResultCode::SUCCEEDED,"Perception failed");
    grasping_msgs::msg::Object target; bool found=false;
    for(const auto& entry:result.result->objects) {
      const auto& o=entry.object;
      if(o.primitives.empty()||o.primitive_poses.empty()) continue;
      const auto& d=o.primitives[0].dimensions; const auto& p=o.primitive_poses[0].position;
      RCLCPP_INFO(logger,"DETECTED: type=%d xyz=(%.4f,%.4f,%.4f)",o.primitives[0].type,p.x,p.y,p.z);
      if(o.primitives[0].type!=shape_msgs::msg::SolidPrimitive::BOX||d.size()!=3) continue;
      if(d[0]<0.015||d[1]<0.015||d[2]<0.02||d[0]>0.08||d[1]>0.08||d[2]>0.10||p.x<0.2||p.x>0.7||std::abs(p.y)>0.4) continue;
      target=o; found=true; break;
    }
    require(found,"No graspable box found in camera point cloud");
    auto position=target.primitive_poses[0].position;
    RCLCPP_INFO(logger,"VISION TARGET: x=%.4f y=%.4f z=%.4f dimensions=(%.4f,%.4f,%.4f)",position.x,position.y,position.z,target.primitives[0].dimensions[0],target.primitives[0].dimensions[1],target.primitives[0].dimensions[2]);
    geometry_msgs::msg::Pose pose; pose.orientation.y=1.0; pose.orientation.w=0.0; pose.position=position; pose.position.z+=0.18;
    set_target(arm,node,pose); execute(arm,logger,"pregrasp from vision");
    pose.position.z=position.z+0.008; cartesian(arm,pose,logger,"approach");
    gripper.setJointValueTarget("robotiq_85_left_knuckle_joint",0.48); execute(gripper,logger,"close gripper");
    std::this_thread::sleep_for(500ms);
    moveit_msgs::msg::AttachedCollisionObject carried;
    carried.link_name="grasp_tcp"; carried.touch_links=gripper.getLinkNames();
    carried.object.id="grasped_box"; carried.object.header.frame_id="world";
    carried.object.primitives=target.primitives; carried.object.primitive_poses=target.primitive_poses;
    carried.object.operation=carried.object.ADD;
    require(scene.applyAttachedCollisionObject(carried),"Could not attach planning collision object");
    pose.position.z+=0.18; cartesian(arm,pose,logger,"lift");
    pose.position.y=-0.25; set_target(arm,node,pose); execute(arm,logger,"transfer");
    pose.position.z=position.z+0.012; cartesian(arm,pose,logger,"lower");
    gripper.setNamedTarget("gripper_open"); execute(gripper,logger,"release");
    carried.object.operation=carried.object.REMOVE;
    require(scene.applyAttachedCollisionObject(carried),"Could not detach planning collision object");
    scene.removeCollisionObjects({"grasped_box"});
    pose.position.z+=0.18; cartesian(arm,pose,logger,"retreat");
    arm.setNamedTarget("home"); execute(arm,logger,"return home");
    RCLCPP_INFO(logger,"MOTION_SEQUENCE_COMPLETE: verify Gazebo object displacement separately");
  } catch(const std::exception& e) { RCLCPP_ERROR(logger,"FAILED: %s",e.what()); code=1; }
  executor.cancel(); spin.join(); rclcpp::shutdown(); return code;
}
