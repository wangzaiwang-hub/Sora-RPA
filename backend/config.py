#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件
"""

# ==================== 数据库配置 ====================
# 使用 MySQL 数据库
DATABASE_TYPE = "mysql"

# MySQL 连接配置
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "sora_management",
    "charset": "utf8mb4"
}

# ==================== 窗口管理配置 ====================
# 后端关闭时是否自动关闭所有窗口
# True: 关闭后端时自动关闭所有通过系统打开的窗口
# False: 关闭后端时保持窗口打开状态
AUTO_CLOSE_WINDOWS_ON_SHUTDOWN = True

# 后端启动时是否自动检测并连接已打开的窗口
# True: 启动时自动检测并连接到已打开的窗口
# False: 启动时不检测已打开的窗口
AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP = True
