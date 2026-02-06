#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理模块 - MySQL 版本
"""

import pymysql
from datetime import datetime
from typing import List, Dict, Optional
import json
import config

class Database:
    def __init__(self):
        self.config = config.MYSQL_CONFIG
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            charset=self.config['charset'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        return conn
    
    def init_database(self):
        """初始化数据库和表"""
        # 首先连接到 MySQL 服务器（不指定数据库）
        conn = pymysql.connect(
            host=self.config['host'],
            port=self.config['port'],
            user=self.config['user'],
            password=self.config['password'],
            charset=self.config['charset']
        )
        cursor = conn.cursor()
        
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {self.config['database']}")
        
        # 账号表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                profile_id INT,
                status VARCHAR(50) DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_username (username),
                INDEX idx_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_id INT,
                profile_id INT,
                prompt TEXT NOT NULL,
                image TEXT,
                model VARCHAR(100),
                status VARCHAR(50) DEFAULT 'pending',
                progress INT DEFAULT 0,
                progress_message TEXT,
                sora_task_id VARCHAR(255),
                generation_id VARCHAR(255),
                post_id VARCHAR(255),
                permalink TEXT,
                is_published TINYINT DEFAULT 0,
                posted_at VARCHAR(255),
                start_time TIMESTAMP NULL,
                end_time TIMESTAMP NULL,
                video_url TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
                INDEX idx_status (status),
                INDEX idx_sora_task_id (sora_task_id),
                INDEX idx_account_id (account_id),
                INDEX idx_profile_id (profile_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 账号表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255),
                user_id VARCHAR(255),
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 视频表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_videos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                video_id VARCHAR(255) NOT NULL UNIQUE,
                account_email VARCHAR(255) NOT NULL,
                url TEXT NOT NULL,
                status VARCHAR(50) NOT NULL,
                prompt TEXT,
                source VARCHAR(100),
                progress INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (account_email) REFERENCES sora_accounts (email) ON DELETE CASCADE,
                INDEX idx_account_email (account_email),
                INDEX idx_status (status),
                INDEX idx_video_id (video_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 抓包视频表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS captured_videos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                post_id VARCHAR(255) NOT NULL UNIQUE,
                text TEXT,
                caption TEXT,
                posted_at DOUBLE,
                updated_at DOUBLE,
                permalink TEXT,
                share_ref VARCHAR(255),
                like_count INT DEFAULT 0,
                view_count INT DEFAULT 0,
                unique_view_count INT DEFAULT 0,
                remix_count INT DEFAULT 0,
                reply_count INT DEFAULT 0,
                user_id VARCHAR(255),
                username VARCHAR(255),
                profile_picture_url TEXT,
                verified TINYINT DEFAULT 0,
                generation_id VARCHAR(255),
                task_id VARCHAR(255),
                video_url TEXT,
                downloadable_url TEXT,
                download_url_watermark TEXT,
                download_url_no_watermark TEXT,
                width INT,
                height INT,
                n_frames INT,
                prompt TEXT,
                source_url TEXT,
                source_size INT,
                thumbnail_url TEXT,
                md_url TEXT,
                ld_url TEXT,
                gif_url TEXT,
                emoji VARCHAR(50),
                discovery_phrase TEXT,
                source VARCHAR(100),
                captured_at VARCHAR(255),
                last_captured_at VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_post_id (post_id),
                INDEX idx_username (username),
                INDEX idx_last_captured_at (last_captured_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255),
                username VARCHAR(255),
                display_name VARCHAR(255),
                profile_picture_url TEXT,
                cover_photo_url TEXT,
                description TEXT,
                location VARCHAR(255),
                website TEXT,
                birthday VARCHAR(50),
                verified TINYINT DEFAULT 0,
                is_phone_number_verified VARCHAR(50),
                is_underage TINYINT DEFAULT 0,
                plan_type VARCHAR(50),
                invite_code VARCHAR(100),
                invite_url TEXT,
                invites_remaining INT,
                num_redemption_gens INT,
                follower_count INT DEFAULT 0,
                following_count INT DEFAULT 0,
                post_count INT DEFAULT 0,
                reply_count INT DEFAULT 0,
                likes_received_count INT DEFAULT 0,
                remix_count INT DEFAULT 0,
                cameo_count INT DEFAULT 0,
                character_count INT DEFAULT 0,
                sora_who_can_message_me VARCHAR(50),
                chatgpt_who_can_message_me VARCHAR(50),
                can_message TINYINT DEFAULT 1,
                can_cameo TINYINT DEFAULT 0,
                calpico_is_enabled TINYINT DEFAULT 1,
                signup_date DOUBLE,
                created_at VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 配额表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_quota (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_email VARCHAR(255),
                user_id VARCHAR(255),
                remaining INT,
                total INT,
                used INT,
                reset_at VARCHAR(255),
                estimated_num_videos_remaining INT,
                estimated_num_purchased_videos_remaining INT,
                credit_remaining INT,
                rate_limit_reached TINYINT DEFAULT 0,
                access_resets_in_seconds INT,
                type_status VARCHAR(100),
                captured_at VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_account_email (account_email),
                INDEX idx_user_id (user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id VARCHAR(255) UNIQUE,
                generation_id VARCHAR(255),
                prompt TEXT,
                status VARCHAR(50),
                task_type VARCHAR(50),
                created_at VARCHAR(255),
                captured_at VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_task_id (task_id),
                INDEX idx_generation_id (generation_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 任务进度表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_task_progress (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL,
                status VARCHAR(50),
                progress_pct DOUBLE,
                prompt TEXT,
                title VARCHAR(500),
                thumbnail_url TEXT,
                failure_reason TEXT,
                captured_at VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_task_captured (task_id, captured_at),
                INDEX idx_task_id (task_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Sora 草稿表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sora_drafts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                draft_id VARCHAR(255) NOT NULL UNIQUE,
                generation_id VARCHAR(255),
                kind VARCHAR(50),
                task_id VARCHAR(255),
                prompt TEXT,
                title VARCHAR(500),
                draft_reviewed TINYINT DEFAULT 0,
                width INT,
                height INT,
                generation_type VARCHAR(50),
                url TEXT,
                downloadable_url TEXT,
                thumbnail_url TEXT,
                reason TEXT,
                reason_str TEXT,
                markdown_reason_str TEXT,
                created_at DOUBLE,
                captured_at VARCHAR(255),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_draft_id (draft_id),
                INDEX idx_task_id (task_id),
                INDEX idx_kind (kind)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        conn.close()
        print("✅ MySQL 数据库初始化完成")

    
    # ==================== 账号管理 ====================
    
    def import_accounts(self, accounts: List) -> int:
        """批量导入账号"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for account in accounts:
            try:
                cursor.execute("""
                    INSERT INTO accounts (username, password, profile_id)
                    VALUES (%s, %s, %s)
                """, (account.username, account.password, account.profile_id))
                count += 1
            except pymysql.IntegrityError:
                # 账号已存在，更新
                cursor.execute("""
                    UPDATE accounts 
                    SET password = %s, profile_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE username = %s
                """, (account.password, account.profile_id, account.username))
                count += 1
        
        conn.commit()
        conn.close()
        return count
    
    def update_task_progress(self, task_id: int, progress: int, message: str = None):
        """更新任务进度"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks 
            SET progress = %s, progress_message = %s
            WHERE id = %s
        """, (progress, message, task_id))
        
        conn.commit()
        conn.close()
    
    def get_all_accounts(self) -> List[Dict]:
        """获取所有账号"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, profile_id, status, created_at, updated_at
            FROM accounts
            ORDER BY id DESC
        """)
        
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    
    def get_account_by_id(self, account_id: int) -> Optional[Dict]:
        """根据ID获取账号"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM accounts WHERE id = %s
        """, (account_id,))
        
        row = cursor.fetchone()
        conn.close()
        return row if row else None
    
    def delete_account(self, account_id: int):
        """删除账号"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 删除相关任务
        cursor.execute("DELETE FROM tasks WHERE account_id = %s", (account_id,))
        # 删除账号
        cursor.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
        
        conn.commit()
        conn.close()
    
    def update_account_status(self, account_id: int, status: str):
        """更新账号状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE accounts 
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (status, account_id))
        
        conn.commit()
        conn.close()

    
    # ==================== 任务管理 ====================
    
    def import_tasks(self, tasks: List) -> int:
        """
        批量导入任务（带去重）
        
        去重规则：
        - 如果提示词和图片都相同，则跳过（不创建重复任务）
        - 如果提示词相同但图片不同，则创建新任务
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        count = 0
        skipped = 0
        
        for task in tasks:
            prompt = task.prompt
            image = task.image
            
            # 检查是否存在相同提示词和图片的任务
            if image:
                # 有图片：检查提示词和图片都相同的任务
                cursor.execute("""
                    SELECT id FROM tasks 
                    WHERE TRIM(prompt) = %s AND image = %s
                    LIMIT 1
                """, (prompt.strip() if prompt else '', image))
            else:
                # 无图片：检查提示词相同且也无图片的任务
                cursor.execute("""
                    SELECT id FROM tasks 
                    WHERE TRIM(prompt) = %s AND (image IS NULL OR image = '')
                    LIMIT 1
                """, (prompt.strip() if prompt else '',))
            
            existing_task = cursor.fetchone()
            
            if existing_task:
                # 任务已存在，跳过
                skipped += 1
                print(f"  ⏭️  跳过重复任务: {prompt[:50]}... (图片: {'有' if image else '无'})")
            else:
                # 任务不存在，创建新任务
                cursor.execute("""
                    INSERT INTO tasks (account_id, profile_id, prompt, image, model)
                    VALUES (%s, %s, %s, %s, %s)
                """, (task.account_id, task.profile_id, task.prompt, task.image, getattr(task, 'model', None)))
                count += 1
                print(f"  ✅ 创建任务: {prompt[:50]}... (图片: {'有' if image else '无'})")
        
        conn.commit()
        conn.close()
        
        print(f"\n📊 导入结果: 创建 {count} 个任务, 跳过 {skipped} 个重复任务")
        return count
    
    def create_task(self, prompt: str, image: str = None, model: str = None, task_id: Optional[int] = None) -> int:
        """创建单个任务（对外API使用）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 如果指定了task_id，检查是否已存在
        if task_id is not None:
            cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
            if cursor.fetchone():
                conn.close()
                raise ValueError(f"任务ID {task_id} 已存在")
            
            # 插入指定ID的任务
            cursor.execute("""
                INSERT INTO tasks (id, prompt, image, model, status, progress)
                VALUES (%s, %s, %s, %s, 'pending', 0)
            """, (task_id, prompt, image, model))
            result_id = task_id
        else:
            # 自动生成ID
            cursor.execute("""
                INSERT INTO tasks (prompt, image, model, status, progress)
                VALUES (%s, %s, %s, 'pending', 0)
            """, (prompt, image, model))
            result_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return result_id
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.*, a.username
            FROM tasks t
            LEFT JOIN accounts a ON t.account_id = a.id
            ORDER BY t.id DESC
        """)
        
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def get_pending_tasks(self, limit: int = None) -> List[Dict]:
        """获取待处理的任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT t.*, a.username, a.password
            FROM tasks t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.status = 'pending'
            ORDER BY t.id ASC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def get_tasks_by_account(self, account_id: int) -> List[Dict]:
        """获取指定账号的任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tasks
            WHERE account_id = %s
            ORDER BY id DESC
        """, (account_id,))
        
        tasks = cursor.fetchall()
        conn.close()
        return tasks
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """根据ID获取任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.*, a.username, a.password
            FROM tasks t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.id = %s
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        return row if row else None
    
    def get_task_by_sora_task_id(self, sora_task_id: str) -> Optional[Dict]:
        """根据Sora任务ID获取任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.*, a.username, a.password
            FROM tasks t
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.sora_task_id = %s
        """, (sora_task_id,))
        
        row = cursor.fetchone()
        conn.close()
        return row if row else None
    
    def update_task_sora_id(self, task_id: int, sora_task_id: str):
        """更新任务的Sora任务ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks 
            SET sora_task_id = %s
            WHERE id = %s
        """, (sora_task_id, task_id))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")

    
    def update_task_status(self, task_id: int, status: str, 
                          start_time: Optional[str] = None,
                          end_time: Optional[str] = None,
                          video_url: Optional[str] = None,
                          error_message: Optional[str] = None):
        """更新任务状态"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        updates = ["status = %s"]
        params = [status]
        
        if start_time:
            updates.append("start_time = %s")
            params.append(start_time)
        
        if end_time:
            updates.append("end_time = %s")
            params.append(end_time)
        
        if video_url:
            updates.append("video_url = %s")
            params.append(video_url)
        
        if error_message:
            updates.append("error_message = %s")
            params.append(error_message)
        
        # 根据状态自动设置 progress 和 progress_message
        if status == 'success' or status == 'published':
            updates.append("progress = %s")
            params.append(100)
            updates.append("progress_message = %s")
            params.append('completed')
        elif status == 'failed':
            updates.append("progress = %s")
            params.append(0)
            if error_message:
                updates.append("progress_message = %s")
                params.append(f'失败: {error_message}')
        elif status == 'running':
            # running 状态不修改 progress_message，保留之前的进度信息
            pass
        
        params.append(task_id)
        
        cursor.execute(f"""
            UPDATE tasks 
            SET {', '.join(updates)}
            WHERE id = %s
        """, params)
        
        conn.commit()
        conn.close()
    
    def delete_task(self, task_id: int):
        """删除任务"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        
        conn.commit()
        conn.close()
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 账号统计
        cursor.execute("SELECT COUNT(*) as total FROM accounts")
        total_accounts = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM accounts WHERE status = 'active'")
        active_accounts = cursor.fetchone()['active']
        
        # 任务统计
        cursor.execute("SELECT COUNT(*) as total FROM tasks")
        total_tasks = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as pending FROM tasks WHERE status = 'pending'")
        pending_tasks = cursor.fetchone()['pending']
        
        cursor.execute("SELECT COUNT(*) as running FROM tasks WHERE status = 'running'")
        running_tasks = cursor.fetchone()['running']
        
        cursor.execute("SELECT COUNT(*) as success FROM tasks WHERE status = 'success'")
        success_tasks = cursor.fetchone()['success']
        
        cursor.execute("SELECT COUNT(*) as failed FROM tasks WHERE status = 'failed'")
        failed_tasks = cursor.fetchone()['failed']
        
        conn.close()
        
        return {
            "accounts": {
                "total": total_accounts,
                "active": active_accounts
            },
            "tasks": {
                "total": total_tasks,
                "pending": pending_tasks,
                "running": running_tasks,
                "success": success_tasks,
                "failed": failed_tasks
            }
        }


    # ==================== Sora 视频管理 ====================
    
    def save_sora_account(self, account_data: dict) -> None:
        """保存或更新 Sora 账号信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO sora_accounts (email, name, user_id, image, updated_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    user_id = VALUES(user_id),
                    image = VALUES(image),
                    updated_at = CURRENT_TIMESTAMP
            """, (
                account_data.get('email'),
                account_data.get('name'),
                account_data.get('id'),
                account_data.get('image')
            ))
            conn.commit()
        finally:
            conn.close()
    
    def save_sora_videos(self, account_email: str, videos_data: dict) -> dict:
        """
        保存 Sora 视频数据，并处理状态变化
        返回统计信息：新增、更新、状态变化的数量
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {
            'new': 0,
            'updated': 0,
            'status_changed': 0
        }
        
        try:
            # 处理所有视频
            all_videos = []
            all_videos.extend(videos_data.get('published', []))
            all_videos.extend(videos_data.get('generating', []))
            all_videos.extend(videos_data.get('unpublished', []))
            
            for video in all_videos:
                video_id = video.get('id')
                url = video.get('url')
                status = video.get('status')
                prompt = video.get('prompt')
                source = video.get('source')
                progress = video.get('progress', 0)
                
                # 检查视频是否已存在
                cursor.execute("""
                    SELECT status FROM sora_videos WHERE video_id = %s
                """, (video_id,))
                existing = cursor.fetchone()
                
                if existing:
                    old_status = existing['status']
                    
                    # 更新视频信息
                    cursor.execute("""
                        UPDATE sora_videos 
                        SET url = %s, status = %s, prompt = %s, source = %s, progress = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE video_id = %s
                    """, (url, status, prompt, source, progress, video_id))
                    
                    stats['updated'] += 1
                    
                    # 检查状态是否变化
                    if old_status != status:
                        stats['status_changed'] += 1
                        print(f"[视频状态变化] {video_id}: {old_status} -> {status}")
                else:
                    # 插入新视频
                    cursor.execute("""
                        INSERT INTO sora_videos (video_id, account_email, url, status, prompt, source, progress)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (video_id, account_email, url, status, prompt, source, progress))
                    
                    stats['new'] += 1
            
            conn.commit()
        finally:
            conn.close()
        
        return stats
    
    def get_sora_videos_by_account(self, account_email: str) -> dict:
        """获取指定账号的所有视频"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT video_id, url, status, prompt, source, progress, created_at, updated_at
                FROM sora_videos
                WHERE account_email = %s
                ORDER BY updated_at DESC
            """, (account_email,))
            
            videos = cursor.fetchall()
            
            # 按状态分类
            result = {
                'published': [],
                'generating': [],
                'unpublished': []
            }
            
            for video in videos:
                video_dict = {
                    'id': video['video_id'],
                    'url': video['url'],
                    'status': video['status'],
                    'prompt': video['prompt'],
                    'source': video['source'],
                    'progress': video['progress'],
                    'timestamp': int(video['updated_at'].timestamp() * 1000) if video['updated_at'] else None
                }
                
                status = video['status']
                
                if status == 'published':
                    result['published'].append(video_dict)
                elif status == 'generating':
                    result['generating'].append(video_dict)
                elif status == 'unpublished':
                    result['unpublished'].append(video_dict)
            
            return result
        finally:
            conn.close()
    
    def get_all_sora_accounts(self) -> List[dict]:
        """获取所有 Sora 账号"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT email, name, user_id, image, created_at, updated_at
                FROM sora_accounts
                ORDER BY updated_at DESC
            """)
            
            accounts = cursor.fetchall()
            return accounts
        finally:
            conn.close()
    
    def delete_sora_video(self, video_id: str) -> dict:
        """删除指定的 Sora 视频，返回被删除视频的信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 先获取视频信息
            cursor.execute("""
                SELECT video_id, url, status, prompt, account_email
                FROM sora_videos WHERE video_id = %s
            """, (video_id,))
            video = cursor.fetchone()
            
            if not video:
                return None
            
            video_info = video
            
            # 删除视频
            cursor.execute("""
                DELETE FROM sora_videos WHERE video_id = %s
            """, (video_id,))
            conn.commit()
            
            return video_info
        finally:
            conn.close()
    
    def batch_delete_sora_videos(self, video_ids: List[str]) -> int:
        """批量删除 Sora 视频"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            placeholders = ','.join(['%s'] * len(video_ids))
            cursor.execute(f"""
                DELETE FROM sora_videos WHERE video_id IN ({placeholders})
            """, video_ids)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
