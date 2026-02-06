#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重置窗口状态
清除所有窗口的运行状态，将它们标记为空闲
"""

import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from window_manager import WindowManager
from database import Database

def reset_window_status():
    """重置所有窗口状态"""
    print("=" * 60)
    print("重置窗口状态")
    print("=" * 60)
    
    db = Database()
    window_manager = WindowManager(db)
    
    # 清空所有窗口状态
    with window_manager.lock:
        profile_ids = list(window_manager.window_status.keys())
        
        if not profile_ids:
            print("没有窗口状态需要重置")
            return
        
        print(f"\n找到 {len(profile_ids)} 个窗口状态记录")
        
        for profile_id in profile_ids:
            status = window_manager.window_status[profile_id]
            print(f"\n窗口 {profile_id}:")
            print(f"  当前状态: {status.get('status')}")
            print(f"  当前任务: {status.get('current_task_id')}")
            
            # 重置为空闲状态
            window_manager.window_status[profile_id] = {
                'status': 'idle',
                'current_task_id': None
            }
            print(f"  ✓ 已重置为空闲状态")
        
        # 清空活动窗口连接
        active_count = len(window_manager.active_windows)
        if active_count > 0:
            print(f"\n清空 {active_count} 个活动窗口连接...")
            window_manager.active_windows.clear()
            print("  ✓ 已清空")
    
    print("\n" + "=" * 60)
    print("✓ 窗口状态已重置")
    print("=" * 60)

if __name__ == "__main__":
    reset_window_status()
