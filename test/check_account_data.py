#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查指定账号的数据 - MySQL 版本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database

def check_account_data(email):
    """检查账号数据"""
    print("=" * 80)
    print(f"检查账号: {email}")
    print("=" * 80)
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 1. 检查 sora_accounts 表
    print("\n📋 1. sora_accounts 表:")
    cursor.execute("""
        SELECT id, email, name, user_id, image, created_at, updated_at
        FROM sora_accounts
        WHERE email = %s
    """, (email,))
    
    account = cursor.fetchone()
    if account:
        print(f"  ✅ 找到账号记录")
        print(f"     ID: {account['id']}")
        print(f"     Email: {account['email']}")
        print(f"     Name: {account['name']}")
        print(f"     User ID: {account['user_id']}")
        image = account['image']
        print(f"     Image: {image[:60] if image else 'N/A'}...")
        print(f"     创建时间: {account['created_at']}")
        print(f"     更新时间: {account['updated_at']}")
    else:
        print(f"  ❌ 未找到账号记录")
    
    # 2. 检查 sora_users 表
    print("\n📋 2. sora_users 表:")
    cursor.execute("""
        SELECT id, user_id, email, username, display_name, 
               profile_picture_url, verified, plan_type,
               follower_count, following_count, post_count,
               created_at, updated_at
        FROM sora_users
        WHERE email = %s
    """, (email,))
    
    user = cursor.fetchone()
    if user:
        print(f"  ✅ 找到用户记录")
        print(f"     ID: {user['id']}")
        print(f"     User ID: {user['user_id']}")
        print(f"     Email: {user['email']}")
        print(f"     Username: {user['username']}")
        print(f"     Display Name: {user['display_name']}")
        pic = user['profile_picture_url']
        print(f"     Profile Picture: {pic[:60] if pic else 'N/A'}...")
        print(f"     Verified: {user['verified']}")
        print(f"     Plan Type: {user['plan_type']}")
        print(f"     关注者: {user['follower_count']}, 关注中: {user['following_count']}, 帖子: {user['post_count']}")
        print(f"     创建时间: {user['created_at']}")
        print(f"     更新时间: {user['updated_at']}")
    else:
        print(f"  ❌ 未找到用户记录")
    
    # 3. 检查 sora_videos 表
    print("\n📋 3. sora_videos 表:")
    cursor.execute("""
        SELECT COUNT(*) as count FROM sora_videos
        WHERE account_email = %s
    """, (email,))
    
    video_count = cursor.fetchone()['count']
    print(f"  视频总数: {video_count}")
    
    if video_count > 0:
        cursor.execute("""
            SELECT video_id, url, status, prompt, progress, created_at, updated_at
            FROM sora_videos
            WHERE account_email = %s
            ORDER BY id DESC
            LIMIT 5
        """, (email,))
        
        print(f"\n  最近 5 个视频:")
        videos = cursor.fetchall()
        for video in videos:
            print(f"\n    Video ID: {video['video_id']}")
            url = video['url']
            print(f"    URL: {url[:60] if url else 'N/A'}...")
            print(f"    状态: {video['status']}")
            prompt = video['prompt']
            print(f"    提示词: {prompt[:50] if prompt else 'N/A'}...")
            print(f"    进度: {video['progress']}%")
            print(f"    创建: {video['created_at']}, 更新: {video['updated_at']}")
    
    # 4. 检查 sora_quota 表
    print("\n📋 4. sora_quota 表:")
    cursor.execute("""
        SELECT id, remaining, total, used, reset_at,
               estimated_num_videos_remaining, credit_remaining,
               account_email, user_id, captured_at
        FROM sora_quota
        WHERE account_email = %s
        ORDER BY id DESC
        LIMIT 1
    """, (email,))
    
    quota = cursor.fetchone()
    if quota:
        print(f"  ✅ 找到配额记录")
        print(f"     ID: {quota['id']}")
        print(f"     剩余/总数/已用: {quota['remaining']}/{quota['total']}/{quota['used']}")
        print(f"     重置时间: {quota['reset_at']}")
        print(f"     预计剩余视频数: {quota['estimated_num_videos_remaining']}")
        print(f"     剩余积分: {quota['credit_remaining']}")
        print(f"     账号邮箱: {quota['account_email']}")
        print(f"     User ID: {quota['user_id']}")
        print(f"     抓包时间: {quota['captured_at']}")
    else:
        print(f"  ❌ 未找到配额记录")
    
    # 5. 检查 captured_videos 表（通过username匹配）
    if user and user['username']:
        username = user['username']
        print(f"\n📋 5. captured_videos 表 (username: {username}):")
        cursor.execute("""
            SELECT COUNT(*) as count FROM captured_videos
            WHERE username = %s
        """, (username,))
        
        captured_count = cursor.fetchone()['count']
        print(f"  抓包视频总数: {captured_count}")
        
        if captured_count > 0:
            cursor.execute("""
                SELECT post_id, prompt, video_url, like_count, view_count, 
                       captured_at, last_captured_at
                FROM captured_videos
                WHERE username = %s
                ORDER BY id DESC
                LIMIT 3
            """, (username,))
            
            print(f"\n  最近 3 个抓包视频:")
            videos = cursor.fetchall()
            for video in videos:
                print(f"\n    Post ID: {video['post_id']}")
                prompt = video['prompt']
                print(f"    提示词: {prompt[:50] if prompt else 'N/A'}...")
                video_url = video['video_url']
                print(f"    视频URL: {video_url[:60] if video_url else 'N/A'}...")
                print(f"    点赞: {video['like_count']}, 观看: {video['view_count']}")
                print(f"    抓包时间: {video['last_captured_at']}")
    
    conn.close()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    email = "xvxqvq.v@gmail.com"
    if len(sys.argv) > 1:
        email = sys.argv[1]
    
    check_account_data(email)
