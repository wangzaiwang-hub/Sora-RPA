#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查并更新超时任务的状态 - MySQL 版本
如果视频实际上已经生成，将任务状态更新为成功
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from datetime import datetime

def check_and_update_tasks():
    """检查超时的任务，看是否有对应的草稿"""
    print("=" * 60)
    print("检查超时任务")
    print("=" * 60)
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 查找所有超时失败的任务
    cursor.execute("""
        SELECT id, sora_task_id, prompt, error_message
        FROM tasks
        WHERE status = 'failed'
        AND error_message LIKE '%超时%'
        ORDER BY id DESC
        LIMIT 20
    """)
    
    failed_tasks = cursor.fetchall()
    
    if not failed_tasks:
        print("没有找到超时失败的任务")
        conn.close()
        return
    
    print(f"\n找到 {len(failed_tasks)} 个超时失败的任务\n")
    
    updated_count = 0
    
    for task in failed_tasks:
        task_id = task['id']
        sora_task_id = task['sora_task_id']
        prompt = task['prompt']
        error_msg = task['error_message']
        
        print(f"任务 {task_id}:")
        print(f"  Sora任务ID: {sora_task_id}")
        print(f"  提示词: {prompt[:50] if prompt else 'N/A'}...")
        print(f"  错误: {error_msg}")
        
        if not sora_task_id:
            print(f"  ⚠️ 没有 Sora 任务ID，跳过")
            continue
        
        # 检查是否有对应的草稿（在 sora_videos 表中）
        cursor.execute("""
            SELECT id, url, status
            FROM sora_videos
            WHERE prompt = %s
            AND status IN ('unpublished', 'published')
            LIMIT 1
        """, (prompt,))
        
        video = cursor.fetchone()
        
        if video:
            video_id = video['id']
            video_url = video['url']
            video_status = video['status']
            print(f"  ✓ 找到对应的视频:")
            print(f"    视频ID: {video_id}")
            print(f"    URL: {video_url}")
            print(f"    状态: {video_status}")
            
            # 更新任务状态为成功
            cursor.execute("""
                UPDATE tasks
                SET status = 'success',
                    video_url = %s,
                    end_time = %s,
                    error_message = NULL
                WHERE id = %s
            """, (video_url, datetime.now().isoformat(), task_id))
            
            print(f"  ✓ 任务状态已更新为 success")
            updated_count += 1
        else:
            print(f"  ⚠️ 未找到对应的视频")
        
        print()
    
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print(f"✓ 完成！共更新 {updated_count} 个任务")
    print("=" * 60)

if __name__ == "__main__":
    check_and_update_tasks()
