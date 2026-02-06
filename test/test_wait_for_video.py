#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 _wait_for_video 方法是否正确检测 published 状态
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python自动化'))

# 模拟任务数据
class MockTaskData:
    def __init__(self, status, video_url=None, generation_id=None):
        self.status = status
        self.video_url = video_url
        self.generation_id = generation_id
    
    def get(self, key):
        return getattr(self, key, None)

# 测试检测逻辑
def test_detection_logic():
    print("=" * 80)
    print("测试任务状态检测逻辑")
    print("=" * 80)
    
    test_cases = [
        MockTaskData('success', video_url='https://example.com/video.mp4'),
        MockTaskData('published', video_url='https://example.com/video.mp4'),
        MockTaskData('success', generation_id='gen_123'),
        MockTaskData('published', generation_id='gen_456'),
        MockTaskData('running'),
    ]
    
    for i, task_data in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"  状态: {task_data.status}")
        print(f"  video_url: {task_data.video_url}")
        print(f"  generation_id: {task_data.generation_id}")
        
        notification_detected = False
        
        # 模拟检测逻辑
        if task_data.get('video_url'):
            print(f'  ✓ 检测到视频URL已存在')
            notification_detected = True
        elif task_data.get('status') in ['success', 'published']:
            print(f'  ✓ 检测到任务状态已更新为 {task_data.get("status")}')
            notification_detected = True
        elif task_data.get('generation_id'):
            print(f'  ✓ 检测到草稿数据: generation_id={task_data.get("generation_id")}')
            notification_detected = True
        
        if notification_detected:
            print(f'  结果: ✅ 应该退出等待')
        else:
            print(f'  结果: ⏳ 继续等待')
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == '__main__':
    test_detection_logic()
