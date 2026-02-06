#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查抓包视频数据 - MySQL 版本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database

def check_captured_videos():
    """检查抓包视频数据"""
    print("=" * 80)
    print("检查抓包视频数据")
    print("=" * 80)
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("""
        SELECT TABLE_NAME FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'captured_videos'
    """, (db.config['database'],))
    
    if not cursor.fetchone():
        print("\n❌ captured_videos 表不存在！")
        conn.close()
        return
    
    print("\n✅ captured_videos 表存在")
    
    # 查看表结构
    print("\n📋 表结构:")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'captured_videos'
        ORDER BY ORDINAL_POSITION
    """, (db.config['database'],))
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['COLUMN_NAME']:30} {col['DATA_TYPE']:15} {'NOT NULL' if col['IS_NULLABLE'] == 'NO' else ''}")
    
    # 查看数据总数
    cursor.execute("SELECT COUNT(*) as count FROM captured_videos")
    total = cursor.fetchone()['count']
    print(f"\n📊 总记录数: {total}")
    
    if total > 0:
        # 查看最近的记录
        print("\n📝 最近 5 条记录:")
        cursor.execute("""
            SELECT id, post_id, username, prompt, video_url, 
                   like_count, view_count, captured_at, last_captured_at
            FROM captured_videos
            ORDER BY id DESC
            LIMIT 5
        """)
        
        records = cursor.fetchall()
        for record in records:
            print(f"\n  ID: {record['id']}")
            print(f"  Post ID: {record['post_id']}")
            print(f"  用户: {record['username']}")
            prompt = record['prompt']
            print(f"  提示词: {prompt[:50] if prompt else 'N/A'}...")
            video_url = record['video_url']
            print(f"  视频URL: {video_url[:60] if video_url else 'N/A'}...")
            print(f"  点赞: {record['like_count']}, 观看: {record['view_count']}")
            print(f"  抓包时间: {record['last_captured_at']}")
    else:
        print("\n⚠️  没有任何记录！")
        print("\n可能的原因:")
        print("  1. 插件没有正确发送数据到后端")
        print("  2. 后端API没有正确保存数据")
        print("  3. 插件配置的API地址不正确")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    check_captured_videos()
