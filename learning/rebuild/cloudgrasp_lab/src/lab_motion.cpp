// Stage 04: choose target -> plan -> optionally execute. No grasp or perception here.
#include <thread>
#include <chrono>
#include <cmath>
#include <future>
#include <moveit_msgs/srv/get_position_ik.hpp>
#include <moveit/robot_state/conversions.hpp>
#include <stdexcept>
#include <rclcpp/rclcpp.hpp>
#include <moveit/move_group_interface/move_group_interface.hpp>
using namespace std::chrono_literals;
using MoveGroup=moveit::planning_interface::MoveGroupInterface;
void require(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
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
  auto n=rclcpp::Node::make_shared("lab_motion",rclcpp::NodeOptions().automatically_declare_parameters_from_overrides(true));
  rclcpp::executors::SingleThreadedExecutor executor; executor.add_node(n);
  std::thread spin([&]{executor.spin();});
  int code=0;
  try {
    moveit::planning_interface::MoveGroupInterface arm(n,"ur_manipulator");
    arm.setPoseReferenceFrame("world"); arm.setEndEffectorLink("grasp_tcp");
    arm.setPlanningTime(10.0); arm.setNumPlanningAttempts(5);
    arm.setMaxVelocityScalingFactor(0.15); arm.setMaxAccelerationScalingFactor(0.15);
    arm.startStateMonitor();
    if(!arm.getCurrentState(5)) throw std::runtime_error("No current joint state");
    arm.setStartStateToCurrentState();
    const auto target=n->get_parameter("target").as_string();
    if(target=="home") arm.setNamedTarget("home");
    else if(target=="pose") {
      geometry_msgs::msg::Pose pose;
      pose.position.x=n->get_parameter("x").as_double();
      pose.position.y=n->get_parameter("y").as_double();
      pose.position.z=n->get_parameter("z").as_double();
      pose.orientation.y=1.; pose.orientation.w=0.;
      set_target(arm,n,pose); // Explicit collision-aware IK seeded by current joint feedback.
    } else throw std::runtime_error("target must be home or pose");
    moveit::planning_interface::MoveGroupInterface::Plan plan;
    if(arm.plan(plan)!=moveit::core::MoveItErrorCode::SUCCESS) throw std::runtime_error("PLAN_FAILED");
    RCLCPP_INFO(n->get_logger(),"PLAN_OK: %zu trajectory points",plan.trajectory.joint_trajectory.points.size());
    if(n->get_parameter("execute").as_bool()) {
      if(arm.execute(plan)!=moveit::core::MoveItErrorCode::SUCCESS) throw std::runtime_error("EXECUTION_FAILED");
      RCLCPP_INFO(n->get_logger(),"EXECUTION_OK");
    } else RCLCPP_INFO(n->get_logger(),"PLAN_ONLY: no motion requested");
  } catch(const std::exception& e) {RCLCPP_ERROR(n->get_logger(),"%s",e.what());code=1;}
  executor.cancel();spin.join();rclcpp::shutdown();return code;
}
