#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查最新任务 - MySQL 版本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import Database

db = Database()
conn = db.get_connection()
cursor = conn.cursor()

cursor.execute('SELECT id, prompt, image, status FROM tasks ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()

print('最新的5个任务:')
print('-' * 100)
for row in rows:
    task_id = row['id']
    prompt = row['prompt']
    image = row['image']
    status = row['status']
    
    print(f'ID: {task_id}')
    print(f'提示词: {prompt[:80]}...' if len(prompt) > 80 else f'提示词: {prompt}')
    print(f'图片: {image if image else "无"}')
    print(f'状态: {status}')
    print('-' * 100)

conn.close()
