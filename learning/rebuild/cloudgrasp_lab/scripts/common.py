import time
import rclpy

def wait(node, future, seconds=15):
    end=time.monotonic()+seconds
    while not future.done():
        if time.monotonic()>end: raise TimeoutError('ROS response timed out')
        rclpy.spin_once(node,timeout_sec=0.1)
    return future.result()
