#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将 captured_videos 表的数据同步到 sora_videos 表
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database

def sync_videos():
    """同步视频数据"""
    print("=" * 80)
    print("同步 captured_videos 到 sora_videos")
    print("=" * 80)
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 获取所有 captured_videos 中的视频
    cursor.execute("""
        SELECT post_id, user_id, username, permalink, source, captured_at
        FROM captured_videos
        ORDER BY id DESC
    """)
    
    captured_videos = cursor.fetchall()
    
    print(f"\n找到 {len(captured_videos)} 个已捕获的视频\n")
    
    synced_count = 0
    skipped_count = 0
    
    for row in captured_videos:
        post_id = row['post_id']
        user_id = row['user_id']
        username = row['username']
        permalink = row['permalink']
        source = row['source']
        captured_at = row['captured_at']
        
        # 查找账号邮箱
        account_email = None
        if user_id:
            cursor.execute("SELECT email FROM sora_accounts WHERE user_id = %s", (user_id,))
            account_row = cursor.fetchone()
            if account_row:
                account_email = account_row['email']
        
        if not account_email:
            account_email = f"{username}@temp.local"
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM sora_videos WHERE video_id = %s", (post_id,))
        existing = cursor.fetchone()
        
        if existing:
            skipped_count += 1
            continue
        
        # 插入到 sora_videos
        try:
            cursor.execute("""
                INSERT INTO sora_videos (
                    video_id, account_email, url, status, source, progress,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                post_id,
                account_email,
                permalink or f"https://sora.chatgpt.com/p/{post_id}",
                'published',
                source,
                100,
                captured_at,
                captured_at
            ))
            
            print(f"✓ 同步: {post_id} ({account_email})")
            synced_count += 1
            
        except Exception as e:
            print(f"✗ 失败: {post_id} - {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"✓ 完成！")
    print(f"  新增: {synced_count} 条")
    print(f"  跳过: {skipped_count} 条（已存在）")
    print("=" * 80)

if __name__ == "__main__":
    sync_videos()
