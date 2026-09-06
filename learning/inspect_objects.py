#!/usr/bin/python3
"""Request perception only and print compact object poses; no robot motion."""
import time
import rclpy
from rclpy.action import ActionClient
from grasping_msgs.action import FindGraspableObjects
from action_msgs.msg import GoalStatus


def wait_for(node, future, seconds):
    deadline = time.monotonic() + seconds
    while not future.done():
        if time.monotonic() >= deadline:
            raise TimeoutError('Perception response timed out; check simulation readiness.')
        rclpy.spin_once(node, timeout_sec=0.1)
    return future.result()


def main():
    rclpy.init()
    node = rclpy.create_node('learning_inspect_objects')
    client = ActionClient(node, FindGraspableObjects, '/find_objects')
    handle = None
    try:
        if not client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError('/find_objects unavailable; start the simulation first.')
        goal = FindGraspableObjects.Goal()
        goal.plan_grasps = False
        print('Requesting object detection only (plan_grasps=False)...', flush=True)
        handle = wait_for(node, client.send_goal_async(goal), 10)
        if not handle.accepted:
            raise RuntimeError('Perception request rejected.')
        response = wait_for(node, handle.get_result_async(), 20)
        if response.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f'Perception action ended with status {response.status}.')
        result = response.result
        print(f'Objects: {len(result.objects)}; support surfaces: {len(result.support_surfaces)}')
        for index, found in enumerate(result.objects, 1):
            obj = found.object
            print(f'Object {index}: name={obj.name!r}, frame={obj.header.frame_id!r}')
            for shape, pose in zip(obj.primitives, obj.primitive_poses):
                p = pose.position
                print(f'  position (m): x={p.x:.6f}, y={p.y:.6f}, z={p.z:.6f}')
                print(f'  shape type={shape.type}, dimensions (m)={list(shape.dimensions)}')
        if not result.objects:
            print('No objects detected; this is not a successful object-location measurement.')
    except (RuntimeError, TimeoutError) as error:
        if handle is not None and handle.accepted:
            try:
                wait_for(node, handle.cancel_goal_async(), 2)
            except Exception:
                pass
        print(f'ERROR: {error}', flush=True)
        return 1
    finally:
        client.destroy()
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
