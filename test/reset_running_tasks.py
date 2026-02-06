#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重置运行中的任务为待处理状态 - MySQL 版本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database

db = Database()
conn = db.get_connection()
cursor = conn.cursor()

cursor.execute("""
    UPDATE tasks 
    SET status = 'pending', profile_id = NULL, start_time = NULL 
    WHERE status = 'running'
""")

count = cursor.rowcount
conn.commit()
conn.close()

print(f'✅ 重置了 {count} 个进行中的任务为待处理状态')
