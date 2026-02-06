# Sora-RPA

自动化管理系统

## 项目结构

```
├── backend/           # 后端服务
│   ├── app.py         # Flask主应用
│   ├── database.py    # 数据库操作
│   ├── window_manager.py  # 窗口管理
│   ├── config.py      # 配置文件
│   └── python自动化/   # 自动化核心模块
├── frontend/          # 前端界面 (Vue + Element Plus)
├── plug-in/           # 插件目录
├── plug-renwu/        # 任务插件
├── docs/              # 文档目录
├── test/              # 测试文件
└── sora_management.sql # 数据库脚本
```

## 快速开始

### 1. 数据库配置

执行数据库脚本创建表结构：
```bash
mysql -u username -p database_name < sora_management.sql
```

### 2. 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 功能特性

- 自动化任务管理
- 窗口控制
- 数据持久化
- 错误截图记录

## 技术栈

- **后端**: Python Flask
- **前端**: Vue 3 + Element Plus
- **数据库**: MySQL
