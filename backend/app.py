#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sora 自动化管理系统 - 后端服务
FastAPI + MySQL
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import json

from database import Database
from window_manager import WindowManager
import config

app = FastAPI(title="Sora 自动化管理系统")

# API 密钥配置
API_SECRET_KEY = "OtEsP8DOVH0lRvWxxIS4PvTCsl6wsAVh"

def verify_api_key(authorization: str = Header(None)):
    """验证 API 密钥"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少 Authorization 头")
    
    # 支持 Bearer token 格式
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    if token != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="无效的 API 密钥")
    
    return token

# 配置 CORS - 添加对私有网络的支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 添加中间件处理私有网络访问
@app.middleware("http")
async def add_private_network_access_headers(request, call_next):
    """添加私有网络访问头，解决 Chrome 的 CORS 限制"""
    response = await call_next(request)
    
    # 允许从公网访问私有网络（localhost）
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    
    return response

# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "管理系统",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Sora 自动化管理系统",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# 初始化数据库和窗口管理器
from database import Database
db = Database()
print("✅ 使用 MySQL 数据库")

window_manager = WindowManager(db)

# ==================== 数据模型 ====================

class AccountImport(BaseModel):
    username: str
    password: str
    profile_id: Optional[int] = None

class TaskImport(BaseModel):
    account_id: Optional[int] = None
    profile_id: Optional[int] = None
    prompt: str
    image: Optional[str] = None

class VideoCreateRequest(BaseModel):
    id: Optional[int] = None
    prompt: str
    image: Optional[str] = None
    model: Optional[str] = None

class WindowControl(BaseModel):
    profile_ids: List[int]
    action: str  # open, close

class ConfigUpdate(BaseModel):
    auto_close_windows_on_shutdown: Optional[bool] = None
    auto_detect_open_windows_on_startup: Optional[bool] = None

# ==================== 账号管理 ====================

@app.post("/api/accounts/import")
async def import_accounts(accounts: List[AccountImport]):
    """批量导入账号"""
    try:
        result = db.import_accounts(accounts)
        return {"success": True, "message": f"成功导入 {result} 个账号"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounts")
async def get_accounts():
    """获取所有账号"""
    try:
        accounts = db.get_all_accounts()
        return {"success": True, "data": accounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int):
    """删除账号"""
    try:
        db.delete_account(account_id)
        return {"success": True, "message": "账号已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 任务管理 ====================

@app.post("/api/tasks/import")
async def import_tasks(tasks: List[TaskImport]):
    """批量导入任务"""
    try:
        result = db.import_tasks(tasks)
        return {"success": True, "message": f"成功导入 {result} 个任务"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/import/file")
async def import_tasks_from_file(file: UploadFile = File(...)):
    """从文件导入任务"""
    try:
        # 读取文件内容
        content = await file.read()
        
        # 解析 JSON
        try:
            data = json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            raise HTTPException(status_code=400, detail="无效的 JSON 格式")
        
        # 验证数据结构
        if 'tasks' not in data:
            print(f"JSON 数据缺少 'tasks' 字段: {data.keys()}")
            raise HTTPException(status_code=400, detail="JSON 文件必须包含 'tasks' 字段")
        
        tasks_data = data['tasks']
        if not isinstance(tasks_data, list):
            print(f"'tasks' 不是数组: {type(tasks_data)}")
            raise HTTPException(status_code=400, detail="'tasks' 必须是数组")
        
        # 转换为 TaskImport 对象
        tasks = []
        for i, task_data in enumerate(tasks_data):
            try:
                task = TaskImport(
                    account_id=task_data.get('account_id'),
                    profile_id=task_data.get('profile_id'),
                    prompt=task_data['prompt'],
                    image=task_data.get('image')
                )
                tasks.append(task)
            except KeyError as e:
                print(f"任务 {i} 缺少必需字段: {e}, 数据: {task_data}")
                raise HTTPException(status_code=400, detail=f"任务 {i} 缺少必需字段: {e}")
            except Exception as e:
                print(f"任务 {i} 解析错误: {e}, 数据: {task_data}")
                raise HTTPException(status_code=400, detail=f"任务 {i} 解析错误: {e}")
        
        # 导入任务
        print(f"准备导入 {len(tasks)} 个任务")
        result = db.import_tasks(tasks)
        print(f"成功导入 {result} 个任务")
        return {"success": True, "message": f"成功从文件导入 {result} 个任务"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"导入任务文件时发生错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def get_tasks(account_id: Optional[int] = None):
    """获取任务列表"""
    try:
        if account_id:
            tasks = db.get_tasks_by_account(account_id)
        else:
            tasks = db.get_all_tasks()
        return {"success": True, "data": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: int):
    """获取单个任务详情"""
    try:
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"success": True, "data": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/execute")
async def execute_task(task_id: int, background_tasks: BackgroundTasks):
    """执行单个任务"""
    try:
        background_tasks.add_task(window_manager.execute_task, task_id)
        return {"success": True, "message": "任务已加入执行队列"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除任务"""
    try:
        db.delete_task(task_id)
        return {"success": True, "message": "任务已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: int):
    """重试失败的任务"""
    try:
        # 获取任务信息
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 重置任务状态
        db.update_task_status(
            task_id,
            'pending',
            start_time=None,
            end_time=None,
            error_message=None,
            video_url=None
        )
        
        # 清除窗口分配（让任务重新进入队列）
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET profile_id = NULL WHERE id = %s", (task_id,))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "任务已重置为待处理状态"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/terminate")
async def terminate_task(task_id: int):
    """终止进行中的任务"""
    try:
        # 获取任务信息
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task['status'] != 'running':
            raise HTTPException(status_code=400, detail="只能终止进行中的任务")
        
        # 重置任务状态为待处理
        db.update_task_status(
            task_id,
            'pending',
            start_time=None,
            end_time=None,
            error_message=None,
            video_url=None
        )
        
        # 清除窗口分配
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET profile_id = NULL WHERE id = %s", (task_id,))
        conn.commit()
        conn.close()
        
        # 如果任务有关联的窗口，将窗口标记为空闲
        if task.get('profile_id'):
            profile_id = task['profile_id']
            with window_manager.lock:
                if profile_id in window_manager.window_status:
                    window_manager.window_status[profile_id] = {
                        'status': 'idle',
                        'current_task_id': None
                    }
            print(f"任务 {task_id} 已被手动终止，窗口 {profile_id} 已释放")
        
        return {"success": True, "message": "任务已终止并退回到待处理队列"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/batch-delete")
async def batch_delete_tasks(task_ids: List[int]):
    """批量删除任务"""
    try:
        for task_id in task_ids:
            db.delete_task(task_id)
        return {"success": True, "message": f"已删除 {len(task_ids)} 个任务"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/batch-retry")
async def batch_retry_tasks(task_ids: List[int]):
    """批量重试失败的任务"""
    try:
        for task_id in task_ids:
            db.update_task_status(
                task_id,
                'pending',
                start_time=None,
                end_time=None,
                error_message=None,
                video_url=None
            )
            # 清除窗口分配
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET profile_id = NULL WHERE id = %s", (task_id,))
            conn.commit()
            conn.close()
        
        return {"success": True, "message": f"已重试 {len(task_ids)} 个任务"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/publish")
async def publish_task_video(task_id: int):
    """
    发布任务的视频到 Sora
    
    要求：
    - 任务状态必须是 success
    - 任务必须有 sora_task_id
    - 任务必须有 video_url
    """
    try:
        # 获取任务信息
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 检查任务状态
        if task['status'] != 'success':
            raise HTTPException(status_code=400, detail=f"任务状态必须是 success，当前状态: {task['status']}")
        
        # 检查是否有 sora_task_id
        sora_task_id = task.get('sora_task_id')
        if not sora_task_id:
            raise HTTPException(status_code=400, detail="任务没有绑定 Sora 任务 ID")
        
        # 检查是否有 video_url
        video_url = task.get('video_url')
        if not video_url:
            raise HTTPException(status_code=400, detail="任务没有视频 URL")
        
        print(f"\n[发布视频] 任务 {task_id}")
        print(f"  Sora 任务 ID: {sora_task_id}")
        print(f"  提示词: {task['prompt'][:50]}...")
        
        # 返回发布所需的信息，由前端/插件执行实际的发布请求
        return {
            "success": True,
            "message": "准备发布视频",
            "data": {
                "task_id": task_id,
                "sora_task_id": sora_task_id,
                "prompt": task['prompt'],
                "video_url": video_url,
                "text": task['prompt'],  # 发布时使用的文本
                "publish_url": "https://sora.chatgpt.com/backend/project_y/post",
                "method": "POST"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[发布视频] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/batch-publish")
async def batch_publish_tasks(task_ids: List[int]):
    """批量发布任务的视频"""
    try:
        results = []
        for task_id in task_ids:
            try:
                task = db.get_task_by_id(task_id)
                if not task:
                    results.append({"task_id": task_id, "success": False, "message": "任务不存在"})
                    continue
                
                if task['status'] != 'success':
                    results.append({"task_id": task_id, "success": False, "message": f"状态不是 success: {task['status']}"})
                    continue
                
                if not task.get('sora_task_id'):
                    results.append({"task_id": task_id, "success": False, "message": "没有 Sora 任务 ID"})
                    continue
                
                if not task.get('video_url'):
                    results.append({"task_id": task_id, "success": False, "message": "没有视频 URL"})
                    continue
                
                results.append({
                    "task_id": task_id,
                    "success": True,
                    "sora_task_id": task['sora_task_id'],
                    "prompt": task['prompt'],
                    "video_url": task['video_url']
                })
                
            except Exception as e:
                results.append({"task_id": task_id, "success": False, "message": str(e)})
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            "success": True,
            "message": f"准备发布 {success_count}/{len(task_ids)} 个视频",
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/publish-callback")
async def publish_callback(data: dict):
    """
    发布成功后的回调
    更新任务的发布信息
    """
    try:
        task_id = data.get('task_id')
        post_id = data.get('post_id')
        permalink = data.get('permalink')
        posted_at = data.get('posted_at')
        
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少 task_id")
        
        print(f"\n[发布回调] 任务 {task_id}")
        print(f"  Post ID: {post_id}")
        print(f"  链接: {permalink}")
        print(f"  发布时间: {posted_at}")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 先检查任务是否存在
        cursor.execute("SELECT id FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            conn.close()
            print(f"  ⚠️ 任务 {task_id} 不存在，跳过更新")
            return {
                "success": False,
                "message": f"任务 {task_id} 不存在"
            }
        
        # 更新任务的发布信息
        cursor.execute("""
            UPDATE tasks
            SET post_id = %s,
                permalink = %s,
                posted_at = %s,
                is_published = 1
            WHERE id = %s
        """, (post_id, permalink, posted_at, task_id))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 任务 {task_id} 发布信息已更新")
        print(f"  ✅ video_url 已更新为: {permalink}\n")
        
        return {
            "success": True,
            "message": "发布信息已更新"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[发布回调] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/tasks/match-by-prompt")
async def match_task_by_prompt(data: dict):
    """
    根据提示词匹配任务并更新视频URL
    
    参数:
    - prompt: 视频的提示词
    - video_url: 视频的URL
    
    返回:
    {
        "success": true/false,
        "message": "匹配结果说明",
        "task_id": 任务ID（如果匹配成功）
    }
    """
    try:
        prompt = data.get('prompt', '').strip()
        video_url = data.get('video_url', '').strip()
        
        if not prompt:
            return {
                "success": False,
                "message": "提示词不能为空"
            }
        
        if not video_url:
            return {
                "success": False,
                "message": "视频URL不能为空"
            }
        
        print(f"\n[提示词匹配] 开始匹配任务")
        print(f"  提示词: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"  视频URL: {video_url}")
        
        # 查询所有运行中的任务（最有可能匹配）
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 先查询运行中的任务
        cursor.execute("""
            SELECT id, prompt, status, start_time
            FROM tasks
            WHERE status = 'running'
            ORDER BY start_time DESC
        """)
        
        running_tasks = cursor.fetchall()
        print(f"  找到 {len(running_tasks)} 个运行中的任务")
        
        # 精确匹配
        for task in running_tasks:
            task_id = task['id']
            task_prompt = task['prompt']
            status = task['status']
            start_time = task['start_time']
            if task_prompt and task_prompt.strip() == prompt:
                print(f"  ✅ 精确匹配成功！任务ID: {task_id}")
                
                # 更新任务状态为成功，并保存视频URL
                db.update_task_status(
                    task_id,
                    'success',
                    end_time=datetime.now().isoformat(),
                    video_url=video_url
                )
                
                conn.close()
                
                return {
                    "success": True,
                    "message": f"任务匹配成功（精确匹配）",
                    "task_id": task_id,
                    "match_type": "exact"
                }
        
        # 如果没有精确匹配，尝试模糊匹配（提示词包含关系）
        for task in running_tasks:
            task_id = task['id']
            task_prompt = task['prompt']
            status = task['status']
            start_time = task['start_time']
            if task_prompt:
                # 检查是否有包含关系（忽略大小写和首尾空格）
                task_prompt_clean = task_prompt.strip().lower()
                prompt_clean = prompt.strip().lower()
                
                if task_prompt_clean in prompt_clean or prompt_clean in task_prompt_clean:
                    print(f"  ✅ 模糊匹配成功！任务ID: {task_id}")
                    print(f"     任务提示词: {task_prompt[:50]}...")
                    print(f"     视频提示词: {prompt[:50]}...")
                    
                    # 更新任务状态
                    db.update_task_status(
                        task_id,
                        'success',
                        end_time=datetime.now().isoformat(),
                        video_url=video_url
                    )
                    
                    conn.close()
                    
                    return {
                        "success": True,
                        "message": f"任务匹配成功（模糊匹配）",
                        "task_id": task_id,
                        "match_type": "fuzzy"
                    }
        
        # 如果运行中的任务都不匹配，查询最近的待处理任务
        cursor.execute("""
            SELECT id, prompt, status, created_at
            FROM tasks
            WHERE status = 'pending'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        pending_tasks = cursor.fetchall()
        print(f"  运行中任务未匹配，检查最近 {len(pending_tasks)} 个待处理任务")
        
        # 精确匹配待处理任务
        for task in pending_tasks:
            task_id = task['id']
            task_prompt = task['prompt']
            status = task['status']
            created_at = task['created_at']
            if task_prompt and task_prompt.strip() == prompt:
                print(f"  ✅ 在待处理任务中找到精确匹配！任务ID: {task_id}")
                
                # 更新任务状态
                db.update_task_status(
                    task_id,
                    'success',
                    start_time=datetime.now().isoformat(),
                    end_time=datetime.now().isoformat(),
                    video_url=video_url
                )
                
                conn.close()
                
                return {
                    "success": True,
                    "message": f"任务匹配成功（待处理任务精确匹配）",
                    "task_id": task_id,
                    "match_type": "exact_pending"
                }
        
        conn.close()
        
        print(f"  ⚠️ 未找到匹配的任务")
        return {
            "success": False,
            "message": "未找到匹配的任务"
        }
        
    except Exception as e:
        print(f"[提示词匹配] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 窗口管理 ====================

@app.post("/api/windows/control")
async def control_windows(control: WindowControl, background_tasks: BackgroundTasks):
    """批量控制窗口"""
    try:
        if control.action == "open":
            result = window_manager.open_windows(control.profile_ids)
            return {"success": True, "data": result}
        elif control.action == "close":
            # 关闭操作改为后台任务，立即返回响应
            background_tasks.add_task(window_manager.close_windows, control.profile_ids)
            return {"success": True, "message": f"正在关闭 {len(control.profile_ids)} 个窗口..."}
        else:
            raise HTTPException(status_code=400, detail="无效的操作")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/windows/status")
async def get_windows_status():
    """获取所有窗口状态"""
    try:
        status = window_manager.get_all_windows_status()
        
        # 为每个窗口添加待处理任务数量和配额信息
        pending_tasks = db.get_pending_tasks()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        for window in status:
            # 统计分配给该窗口的待处理任务
            window_pending = sum(1 for t in pending_tasks if t.get('profile_id') == window['profile_id'])
            window['pending_tasks'] = window_pending
            
            # 🆕 获取该窗口关联账号的配额信息
            window['quota_remaining'] = None
            window_name = window.get('name', '')
            
            # 尝试从窗口名称中提取邮箱（窗口名称通常就是邮箱）
            try:
                # 方法1: 窗口名称直接匹配邮箱
                if '@' in window_name:
                    cursor.execute("""
                        SELECT sq.estimated_num_videos_remaining
                        FROM sora_quota sq
                        WHERE sq.account_email = %s
                        ORDER BY sq.created_at DESC
                        LIMIT 1
                    """, (window_name,))
                    result = cursor.fetchone()
                    
                    if result and result['estimated_num_videos_remaining'] is not None:
                        window['quota_remaining'] = result['estimated_num_videos_remaining']
                        window['account_email'] = window_name
                        
            except Exception as e:
                print(f"  ⚠️ 获取窗口 {window['profile_id']} 配额失败: {e}")
        
        conn.close()
        
        # 添加未分配窗口的任务数量
        unassigned_tasks = sum(1 for t in pending_tasks if not t.get('profile_id'))
        
        # 🆕 按配额剩余次数降序排序（次数多的在前面，None 值放最后）
        status.sort(key=lambda x: (x['quota_remaining'] is None, -(x['quota_remaining'] or 0)))
        
        return {
            "success": True, 
            "data": status,
            "unassigned_tasks": unassigned_tasks
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/windows/{profile_id}/status")
async def get_window_status(profile_id: int):
    """获取单个窗口状态"""
    try:
        status = window_manager.get_window_status(profile_id)
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 统计信息 ====================

@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    try:
        stats = db.get_statistics()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 账号视频统计 ====================

class VideoStatsData(BaseModel):
    totalVideos: int
    publishedVideos: int
    generatingVideos: int
    unpublishedVideos: int
    videos: dict
    account: Optional[dict] = None
    lastUpdate: str

@app.post("/v1/videos/stats")
async def update_video_stats(stats: VideoStatsData):
    """
    接收插件发送的视频统计数据
    
    数据格式:
    {
        "totalVideos": 10,
        "publishedVideos": 5,
        "generatingVideos": 2,
        "unpublishedVideos": 3,
        "videos": {
            "published": [...],
            "generating": [...],
            "unpublished": [...]
        },
        "account": {
            "email": "user@example.com",
            "name": "User Name",
            "id": "user_id"
        },
        "lastUpdate": "2024-01-30..."
    }
    """
    try:
        print(f"[视频统计] 收到统计数据:")
        print(f"  原始 account 数据: {stats.account}")
        print(f"  账号: {stats.account.get('email') if stats.account else 'Unknown'}")
        print(f"  总视频数: {stats.totalVideos}")
        print(f"  已发布: {stats.publishedVideos}")
        print(f"  生成中: {stats.generatingVideos}")
        print(f"  未发布: {stats.unpublishedVideos}")
        
        # 保存到数据库
        if stats.account and stats.account.get('email'):
            account_email = stats.account.get('email')
            
            # 保存账号信息
            db.save_sora_account(stats.account)
            print(f"  ✅ 账号信息已保存: {account_email}")
            
            # 保存视频数据
            save_stats = db.save_sora_videos(account_email, stats.videos)
            print(f"  ✅ 视频数据已保存: 新增 {save_stats['new']}, 更新 {save_stats['updated']}, 状态变化 {save_stats['status_changed']}")
        
        # 同时保存到内存（用于快速访问）
        if not hasattr(app.state, 'video_stats'):
            app.state.video_stats = {}
        
        app.state.video_stats = {
            "totalVideos": stats.totalVideos,
            "publishedVideos": stats.publishedVideos,
            "generatingVideos": stats.generatingVideos,
            "unpublishedVideos": stats.unpublishedVideos,
            "videos": stats.videos,
            "account": stats.account,
            "lastUpdate": stats.lastUpdate
        }
        
        return {
            "success": True,
            "message": "统计数据已接收并保存"
        }
    except Exception as e:
        print(f"[视频统计] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/videos/stats")
async def get_video_stats():
    """获取视频统计数据（从数据库读取所有账号）"""
    try:
        # 获取所有账号
        accounts = db.get_all_sora_accounts()
        
        if not accounts:
            return {
                "success": True,
                "data": {
                    "accounts": []
                }
            }
        
        # 获取每个账号的视频数据
        accounts_data = []
        for account in accounts:
            account_email = account['email']
            user_id = account['user_id']
            
            # 从数据库获取该账号的所有视频
            videos = db.get_sora_videos_by_account(account_email)
            
            # 🆕 获取该账号的最新配额信息（按账号查询）
            quota_remaining = None
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT estimated_num_videos_remaining, credit_remaining
                    FROM sora_quota
                    WHERE account_email = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (account_email,))
                quota_row = cursor.fetchone()
                if quota_row:
                    quota_remaining = quota_row['estimated_num_videos_remaining']
                conn.close()
            except Exception as e:
                print(f"  ⚠️ 获取账号 {account_email} 配额失败: {e}")
            
            # 计算统计数据
            total_videos = len(videos['published']) + len(videos['generating']) + len(videos['unpublished'])
            
            accounts_data.append({
                "account": {
                    "email": account['email'],
                    "name": account['name'],
                    "id": account['user_id'],
                    "image": account['image']
                },
                "totalVideos": total_videos,
                "publishedVideos": len(videos['published']),
                "generatingVideos": len(videos['generating']),
                "unpublishedVideos": len(videos['unpublished']),
                "quotaRemaining": quota_remaining,  # 🆕 剩余次数
                "videos": videos,
                "lastUpdate": account['updated_at']
            })
        
        # 🆕 按剩余次数降序排序（次数多的在前面，None 值放最后）
        accounts_data.sort(key=lambda x: (x['quotaRemaining'] is None, -(x['quotaRemaining'] or 0)))
        
        return {
            "success": True,
            "data": {
                "accounts": accounts_data
            }
        }
    except Exception as e:
        print(f"[获取视频统计] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/account/stats")
async def update_account_stats(stats: dict):
    """
    更新账号视频统计数据（来自插件）
    
    数据格式:
    {
        "totalVideos": 10,
        "publishedVideos": 5,
        "unpublishedVideos": 5,
        "draftVideos": 3,
        "publishedUrls": ["url1", "url2"],
        "videos": [
            {
                "type": "published",
                "url": "...",
                "prompt": "...",
                "published": true
            }
        ],
        "lastUpdate": "2024-01-30..."
    }
    """
    try:
        print(f"[账号统计] 收到统计数据:")
        print(f"  总视频数: {stats.get('totalVideos', 0)}")
        print(f"  已发布: {stats.get('publishedVideos', 0)}")
        print(f"  未发布: {stats.get('unpublishedVideos', 0)}")
        print(f"  草稿: {stats.get('draftVideos', 0)}")
        print(f"  已发布URL数: {len(stats.get('publishedUrls', []))}")
        
        # 保存到数据库（可选）
        # 这里可以添加保存逻辑
        
        return {
            "success": True,
            "message": "统计数据已接收",
            "data": stats
        }
    except Exception as e:
        print(f"[账号统计] 处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/account/stats")
async def get_account_stats():
    """获取账号视频统计数据"""
    try:
        # 这里可以从数据库读取
        # 暂时返回空数据
        return {
            "success": True,
            "data": {
                "totalVideos": 0,
                "publishedVideos": 0,
                "unpublishedVideos": 0,
                "draftVideos": 0,
                "publishedUrls": [],
                "videos": []
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/videos/{video_id}/delete")
async def delete_video(video_id: str):
    """删除指定的视频"""
    try:
        video_info = db.delete_sora_video(video_id)
        if video_info:
            return {
                "success": True,
                "message": "视频已删除",
                "data": {
                    "video_id": video_info['video_id'],
                    "url": video_info['url'],
                    "status": video_info['status'],
                    "prompt": video_info['prompt'],
                    "account_email": video_info['account_email']
                }
            }
        else:
            raise HTTPException(status_code=404, detail="视频不存在")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[删除视频] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/videos/batch-delete")
async def batch_delete_videos(video_ids: List[str]):
    """批量删除视频"""
    try:
        count = db.batch_delete_sora_videos(video_ids)
        return {
            "success": True,
            "message": f"已删除 {count} 个视频"
        }
    except Exception as e:
        print(f"[批量删除视频] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/debug/prompt-extraction")
async def debug_prompt_extraction(data: dict):
    """接收提示词提取的调试日志"""
    try:
        print("\n" + "="*80)
        print("[提示词提取调试]")
        print(f"URL: {data.get('url')}")
        print(f"视频ID: {data.get('videoId')}")
        print(f"提取结果: {data.get('prompt')}")
        print("\n详细日志:")
        for log in data.get('logs', []):
            print(f"  {log}")
        print("="*80 + "\n")
        
        return {"success": True}
    except Exception as e:
        print(f"[调试日志] 处理失败: {e}")
        return {"success": False, "error": str(e)}

@app.post("/v1/debug/test")
async def debug_test(data: dict):
    """接收测试日志"""
    try:
        print(f"\n[测试日志] {data.get('message')}")
        print(f"  URL: {data.get('url')}")
        print(f"  时间: {data.get('timestamp')}\n")
        return {"success": True}
    except Exception as e:
        print(f"[测试日志] 处理失败: {e}")
        return {"success": False, "error": str(e)}

# ==================== 多类型数据接收接口 ====================

@app.post("/api/data/capture")
async def capture_data(data: dict):
    """
    接收插件捕获的各种类型数据
    
    支持的类型:
    - USER_INFO: 用户信息
    - QUOTA: 配额信息
    - CREATE_VIDEO: 创建视频
    - VIDEO_PROGRESS: 视频进度
    - VIDEO_DETAIL: 视频详情
    - DRAFT: 草稿信息
    """
    try:
        data_type = data.get('type')
        data_content = data.get('data')
        
        print(f"\n[数据捕获] 收到 {data_type} 类型数据")
        
        if data_type == 'USER_INFO':
            return await handle_user_info(data_content)
        elif data_type == 'QUOTA':
            return await handle_quota(data_content)
        elif data_type == 'CREATE_VIDEO':
            return await handle_create_video(data_content)
        elif data_type == 'VIDEO_PROGRESS':
            return await handle_video_progress(data_content)
        elif data_type == 'VIDEO_DETAIL':
            return await capture_video(data_content)
        elif data_type == 'DRAFT':
            return await handle_draft(data_content)
        elif data_type == 'PUBLISHED_VIDEO':
            return await handle_published_video(data_content)
        else:
            return {"success": False, "message": f"未知的数据类型: {data_type}"}
            
    except Exception as e:
        print(f"[数据捕获] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# 处理用户信息
async def handle_user_info(data: dict):
    try:
        print(f"  用户ID: {data.get('user_id')}")
        print(f"  邮箱: {data.get('email')}")
        print(f"  用户名: {data.get('username')}")
        print(f"  邀请码: {data.get('invite_code')}")
        print(f"  剩余邀请: {data.get('invites_remaining')}")
        
        # 🆕 先保存到 sora_accounts 表（用于视频统计页面）
        if data.get('email') and data.get('user_id'):
            db.save_sora_account({
                'email': data.get('email'),
                'name': data.get('display_name') or data.get('username') or data.get('email').split('@')[0],
                'id': data.get('user_id'),
                'image': data.get('profile_picture_url')
            })
            print(f"  ✅ 账号信息已保存到 sora_accounts")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 保存或更新用户信息（包含所有新字段）
        cursor.execute("""
            INSERT INTO sora_users (
                user_id, email, username, display_name,
                profile_picture_url, cover_photo_url, description,
                location, website, birthday,
                verified, is_phone_number_verified, is_underage,
                plan_type,
                invite_code, invite_url, invites_remaining, num_redemption_gens,
                follower_count, following_count, post_count, reply_count,
                likes_received_count, remix_count, cameo_count, character_count,
                sora_who_can_message_me, chatgpt_who_can_message_me,
                can_message, can_cameo, calpico_is_enabled,
                signup_date, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
                email = VALUES(email),
                username = VALUES(username),
                display_name = VALUES(display_name),
                profile_picture_url = VALUES(profile_picture_url),
                cover_photo_url = VALUES(cover_photo_url),
                description = VALUES(description),
                location = VALUES(location),
                website = VALUES(website),
                birthday = VALUES(birthday),
                verified = VALUES(verified),
                is_phone_number_verified = VALUES(is_phone_number_verified),
                is_underage = VALUES(is_underage),
                plan_type = VALUES(plan_type),
                invite_code = VALUES(invite_code),
                invite_url = VALUES(invite_url),
                invites_remaining = VALUES(invites_remaining),
                num_redemption_gens = VALUES(num_redemption_gens),
                follower_count = VALUES(follower_count),
                following_count = VALUES(following_count),
                post_count = VALUES(post_count),
                reply_count = VALUES(reply_count),
                likes_received_count = VALUES(likes_received_count),
                remix_count = VALUES(remix_count),
                cameo_count = VALUES(cameo_count),
                character_count = VALUES(character_count),
                sora_who_can_message_me = VALUES(sora_who_can_message_me),
                chatgpt_who_can_message_me = VALUES(chatgpt_who_can_message_me),
                can_message = VALUES(can_message),
                can_cameo = VALUES(can_cameo),
                calpico_is_enabled = VALUES(calpico_is_enabled),
                signup_date = VALUES(signup_date),
                created_at = VALUES(created_at),
                updated_at = CURRENT_TIMESTAMP
        """, (
            data.get('user_id'),
            data.get('email'),
            data.get('username'),
            data.get('display_name'),
            data.get('profile_picture_url'),
            data.get('cover_photo_url'),
            data.get('description'),
            data.get('location'),
            data.get('website'),
            data.get('birthday'),
            1 if data.get('verified') else 0,
            data.get('is_phone_number_verified'),
            1 if data.get('is_underage') else 0,
            data.get('plan_type'),
            data.get('invite_code'),
            data.get('invite_url'),
            data.get('invites_remaining'),
            data.get('num_redemption_gens'),
            data.get('follower_count', 0),
            data.get('following_count', 0),
            data.get('post_count', 0),
            data.get('reply_count', 0),
            data.get('likes_received_count', 0),
            data.get('remix_count', 0),
            data.get('cameo_count', 0),
            data.get('character_count', 0),
            data.get('sora_who_can_message_me'),
            data.get('chatgpt_who_can_message_me'),
            1 if data.get('can_message') else 0,
            1 if data.get('can_cameo') else 0,
            1 if data.get('calpico_is_enabled') else 0,
            data.get('signup_date'),
            data.get('created_at')
        ))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 用户信息已保存到 sora_users\n")
        return {"success": True, "message": "用户信息已保存"}
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}\n")
        raise

# 处理配额信息
async def handle_quota(data: dict):
    try:
        account_email = data.get('account_email')
        user_id = data.get('user_id')
        
        print(f"  账号: {account_email or '未知'}")
        print(f"  剩余视频数: {data.get('estimated_num_videos_remaining')}")
        print(f"  剩余积分: {data.get('credit_remaining')}")
        print(f"  速率限制: {data.get('rate_limit_reached')}")
        print(f"  重置时间: {data.get('access_resets_in_seconds')} 秒")
        
        # 🆕 先保存账号信息到 sora_accounts 表
        if account_email and user_id:
            db.save_sora_account({
                'email': account_email,
                'name': data.get('name', account_email.split('@')[0]),  # 如果没有名字，用邮箱前缀
                'id': user_id,
                'image': data.get('image')
            })
            print(f"  ✅ 账号信息已保存")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 🆕 保存配额信息（包含账号信息）
        cursor.execute("""
            INSERT INTO sora_quota (
                account_email, user_id,
                remaining, total, used, reset_at,
                estimated_num_videos_remaining,
                estimated_num_purchased_videos_remaining,
                credit_remaining,
                rate_limit_reached,
                access_resets_in_seconds,
                type_status,
                captured_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            account_email,
            user_id,
            data.get('remaining'),
            data.get('total'),
            data.get('used'),
            data.get('reset_at'),
            data.get('estimated_num_videos_remaining'),
            data.get('estimated_num_purchased_videos_remaining'),
            data.get('credit_remaining'),
            1 if data.get('rate_limit_reached') else 0,
            data.get('access_resets_in_seconds'),
            data.get('type_status'),
            data.get('captured_at')
        ))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 配额信息已保存\n")
        return {"success": True, "message": "配额信息已保存"}
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}\n")
        raise


# 处理创建视频
async def handle_create_video(data: dict):
    try:
        sora_task_id = data.get('task_id')
        prompt = data.get('prompt')
        status = data.get('status')
        
        print(f"  Sora任务ID: {sora_task_id or '(未提取到)'}")
        print(f"  提示词: {prompt or '(无)'}")
        print(f"  状态: {status or '(无)'}")
        
        # 如果没有task_id，记录警告但继续处理
        if not sora_task_id:
            print(f"  ⚠️ 警告: 未能提取 task_id，可能是带图片的请求")
            print(f"  💡 将通过后续的 DRAFT 数据进行匹配")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 保存创建记录到 sora_tasks 表（task_id可以为NULL）
        cursor.execute("""
            INSERT INTO sora_tasks (
                task_id, generation_id, prompt, status,
                task_type, created_at, captured_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            sora_task_id,  # 可以为 None
            data.get('generation_id'),
            prompt,
            status,
            data.get('task_type'),
            data.get('created_at'),
            data.get('captured_at')
        ))
        
        conn.commit()
        print(f"  ✅ 保存成功")
        
        # 只有当有task_id时才尝试匹配
        matched_task_id = None
        if sora_task_id and prompt:
            print(f"  🔍 尝试匹配任务...")
            
            # 查询所有运行中或待处理的任务
            cursor.execute("""
                SELECT id, prompt, status, sora_task_id
                FROM tasks
                WHERE status IN ('running', 'pending')
                AND sora_task_id IS NULL
                ORDER BY 
                    CASE WHEN status = 'running' THEN 0 ELSE 1 END,
                    id DESC
            """)
            
            tasks = cursor.fetchall()
            print(f"  找到 {len(tasks)} 个待匹配的任务")
            
            # 精确匹配
            for task in tasks:
                task_id = task['id']
                task_prompt = task['prompt']
                task_status = task['status']
                existing_sora_id = task['sora_task_id']
                if task_prompt and task_prompt.strip() == prompt.strip():
                    print(f"  ✅ 精确匹配成功！任务ID: {task_id}")
                    
                    # 更新任务的 sora_task_id
                    cursor.execute("""
                        UPDATE tasks 
                        SET sora_task_id = %s,
                            status = 'running',
                            start_time = CASE WHEN start_time IS NULL THEN %s ELSE start_time END
                        WHERE id = %s
                    """, (sora_task_id, datetime.now().isoformat(), task_id))
                    
                    conn.commit()
                    matched_task_id = task_id
                    print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                    break
            
            # 如果没有精确匹配，尝试模糊匹配
            if not matched_task_id:
                for task in tasks:
                    task_id = task['id']
                    task_prompt = task['prompt']
                    task_status = task['status']
                    existing_sora_id = task['sora_task_id']
                    if task_prompt:
                        task_prompt_clean = task_prompt.strip().lower()
                        prompt_clean = prompt.strip().lower()
                        
                        if task_prompt_clean in prompt_clean or prompt_clean in task_prompt_clean:
                            print(f"  ✅ 模糊匹配成功！任务ID: {task_id}")
                            print(f"     任务提示词: {task_prompt[:50]}...")
                            print(f"     Sora提示词: {prompt[:50]}...")
                            
                            # 更新任务的 sora_task_id
                            cursor.execute("""
                                UPDATE tasks 
                                SET sora_task_id = %s,
                                    status = 'running',
                                    start_time = CASE WHEN start_time IS NULL THEN %s ELSE start_time END
                                WHERE id = %s
                            """, (sora_task_id, datetime.now().isoformat(), task_id))
                            
                            conn.commit()
                            matched_task_id = task_id
                            print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                            break
            
            if not matched_task_id:
                print(f"  ⚠️ 未找到匹配的任务")
        
        conn.close()
        
        print(f"  ✅ 创建记录已保存\n")
        return {
            "success": True, 
            "message": "创建记录已保存", 
            "task_id": sora_task_id,
            "matched_task_id": matched_task_id
        }
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}\n")
        raise

# 处理视频进度
async def handle_video_progress(data: dict):
    try:
        sora_task_id = data.get('task_id')
        status = data.get('status')
        
        print(f"  Sora任务ID: {sora_task_id}")
        print(f"  状态: {status}")
        
        # progress_pct 可能是 None（在 preprocessing 状态时）
        progress_pct = data.get('progress_pct')
        if progress_pct is not None:
            print(f"  进度: {progress_pct * 100:.1f}%")
        else:
            print(f"  进度: 未知")
        
        # 显示提示词
        prompt = data.get('prompt')
        if prompt:
            print(f"  提示词: {prompt}")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 更新或插入进度记录到 sora_task_progress 表
        cursor.execute("""
            INSERT INTO sora_task_progress (
                task_id, status, progress_pct, prompt,
                title, thumbnail_url, failure_reason, captured_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                progress_pct = VALUES(progress_pct),
                prompt = VALUES(prompt),
                title = VALUES(title),
                thumbnail_url = VALUES(thumbnail_url),
                failure_reason = VALUES(failure_reason)
        """, (
            sora_task_id,
            status,
            progress_pct,
            prompt,
            data.get('title'),
            data.get('thumbnail_url'),
            data.get('failure_reason'),
            data.get('captured_at')
        ))
        
        # 查找绑定了这个 sora_task_id 的任务
        cursor.execute("""
            SELECT id, prompt, status, video_url
            FROM tasks
            WHERE sora_task_id = %s
        """, (sora_task_id,))
        
        task = cursor.fetchone()
        
        if task:
            task_id = task['id']
            task_prompt = task['prompt']
            task_status = task['status']
            task_video_url = task['video_url']
            print(f"  📌 找到绑定的任务: ID={task_id}")
            
            # 更新任务进度
            if progress_pct is not None:
                progress_int = int(progress_pct * 100)
                cursor.execute("""
                    UPDATE tasks
                    SET progress = %s,
                        progress_message = %s
                    WHERE id = %s
                """, (progress_int, status, task_id))
                print(f"  ✅ 任务进度已更新: {progress_int}%")
            
            # 如果状态是 completed 且有 generations，说明视频生成完成
            generations = data.get('generations', [])
            if status == 'completed' and len(generations) > 0:
                # 获取第一个生成的视频
                first_gen = generations[0]
                generation_id = first_gen.get('id')  # 如 gen_xxx
                
                # 优先使用 downloadable_url，如果没有则使用 id 构造页面URL
                video_url = first_gen.get('downloadable_url')
                
                if not video_url and generation_id:
                    # 如果没有 downloadable_url，使用 generation_id 构造草稿页面URL
                    video_url = f"https://sora.chatgpt.com/d/{generation_id}"
                
                if video_url:
                    print(f"  🎉 视频生成完成！")
                    print(f"  生成ID: {generation_id}")
                    print(f"  视频URL: {video_url}")
                    
                    # 更新任务状态为成功
                    cursor.execute("""
                        UPDATE tasks
                        SET status = 'success',
                            video_url = %s,
                            end_time = %s,
                            progress = 100,
                            progress_message = 'completed'
                        WHERE id = %s
                    """, (video_url, datetime.now().isoformat(), task_id))
                    
                    print(f"  ✅ 任务 {task_id} 已标记为成功")
                else:
                    print(f"  ⚠️ 视频生成完成但未找到URL")
            
            # 如果状态是 failed，更新任务状态
            elif status == 'failed':
                failure_reason = data.get('failure_reason', '未知错误')
                print(f"  ❌ 视频生成失败: {failure_reason}")
                
                cursor.execute("""
                    UPDATE tasks
                    SET status = 'failed',
                        error_message = %s,
                        end_time = %s
                    WHERE id = %s
                """, (failure_reason, datetime.now().isoformat(), task_id))
                
                print(f"  ✅ 任务 {task_id} 已标记为失败")
        else:
            # 未找到绑定的任务，尝试通过提示词匹配并绑定
            print(f"  ⚠️ 未找到绑定的任务，尝试通过提示词匹配...")
            
            if prompt:
                # 查询所有运行中、待处理或已成功但未绑定的任务
                cursor.execute("""
                    SELECT id, prompt, status
                    FROM tasks
                    WHERE status IN ('running', 'pending', 'success')
                    AND sora_task_id IS NULL
                    ORDER BY 
                        CASE 
                            WHEN status = 'running' THEN 0 
                            WHEN status = 'pending' THEN 1
                            WHEN status = 'success' THEN 2
                            ELSE 3
                        END,
                        id DESC
                """)
                
                tasks = cursor.fetchall()
                print(f"  找到 {len(tasks)} 个待匹配的任务")
                
                matched_task_id = None
                
                # 精确匹配
                for task_row in tasks:
                    task_id = task_row['id']
                    task_prompt = task_row['prompt']
                    task_status = task_row['status']
                    if task_prompt and task_prompt.strip() == prompt.strip():
                        print(f"  ✅ 精确匹配成功！任务ID: {task_id}")
                        
                        # 更新任务的 sora_task_id
                        cursor.execute("""
                            UPDATE tasks 
                            SET sora_task_id = %s,
                                status = 'running',
                                start_time = CASE WHEN start_time IS NULL THEN %s ELSE start_time END
                            WHERE id = %s
                        """, (sora_task_id, datetime.now().isoformat(), task_id))
                        
                        matched_task_id = task_id
                        print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                        
                        # 更新进度
                        if progress_pct is not None:
                            progress_int = int(progress_pct * 100)
                            cursor.execute("""
                                UPDATE tasks
                                SET progress = %s,
                                    progress_message = %s
                                WHERE id = %s
                            """, (progress_int, status, task_id))
                            print(f"  ✅ 任务进度已更新: {progress_int}%")
                        
                        break
                
                # 如果没有精确匹配，尝试模糊匹配
                if not matched_task_id:
                    for task_row in tasks:
                        task_id = task_row['id']
                        task_prompt = task_row['prompt']
                        task_status = task_row['status']
                        if task_prompt:
                            task_prompt_clean = task_prompt.strip().lower()
                            prompt_clean = prompt.strip().lower()
                            
                            if task_prompt_clean in prompt_clean or prompt_clean in task_prompt_clean:
                                print(f"  ✅ 模糊匹配成功！任务ID: {task_id}")
                                print(f"     任务提示词: {task_prompt[:50]}...")
                                print(f"     Sora提示词: {prompt[:50]}...")
                                
                                # 更新任务的 sora_task_id
                                cursor.execute("""
                                    UPDATE tasks 
                                    SET sora_task_id = %s,
                                        status = 'running',
                                        start_time = CASE WHEN start_time IS NULL THEN %s ELSE start_time END
                                    WHERE id = %s
                                """, (sora_task_id, datetime.now().isoformat(), task_id))
                                
                                matched_task_id = task_id
                                print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                                
                                # 更新进度
                                if progress_pct is not None:
                                    progress_int = int(progress_pct * 100)
                                    cursor.execute("""
                                        UPDATE tasks
                                        SET progress = %s,
                                            progress_message = %s
                                        WHERE id = %s
                                    """, (progress_int, status, task_id))
                                    print(f"  ✅ 任务进度已更新: {progress_int}%")
                                
                                break
                
                if not matched_task_id:
                    print(f"  ⚠️ 未找到匹配的任务")
            else:
                print(f"  ⚠️ 没有提示词，无法匹配任务")
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 进度已更新\n")
        return {"success": True, "message": "进度已更新"}
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}\n")
        raise

# 处理草稿信息
async def handle_draft(data: dict):
    """
    处理草稿信息，用于绑定任务ID和更新视频URL
    
    草稿数据包含:
    - id: 生成ID (gen_xxx)
    - task_id: Sora任务ID (task_xxx)
    - prompt: 提示词
    - downloadable_url: 可下载的视频URL
    - kind: 类型 (sora_draft 或 sora_content_violation)
    """
    try:
        draft_id = data.get('id')
        sora_task_id = data.get('task_id')
        prompt = data.get('prompt')
        downloadable_url = data.get('downloadable_url')
        kind = data.get('kind')
        
        print(f"  草稿ID: {draft_id}")
        print(f"  Sora任务ID: {sora_task_id}")
        print(f"  类型: {kind}")
        
        if prompt:
            print(f"  提示词: {prompt}")
        
        if downloadable_url:
            print(f"  视频URL: {downloadable_url[:80]}...")
        
        # 如果是内容违规，记录但不处理
        if kind == 'sora_content_violation':
            reason = data.get('reason_str', '未知原因')
            print(f"  ⚠️ 内容违规: {reason}")
            
            # 如果有绑定的任务，更新为失败状态
            if sora_task_id:
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id FROM tasks WHERE sora_task_id = %s
                """, (sora_task_id,))
                
                task = cursor.fetchone()
                if task:
                    task_id = task['id']
                    cursor.execute("""
                        UPDATE tasks
                        SET status = 'failed',
                            error_message = %s,
                            end_time = %s
                        WHERE id = %s
                    """, (f"内容违规: {reason}", datetime.now().isoformat(), task_id))
                    
                    conn.commit()
                    print(f"  ✅ 任务 {task_id} 已标记为失败（内容违规）")
                
                conn.close()
            
            return {"success": True, "message": "内容违规已记录"}
        
        # 处理正常草稿
        if not sora_task_id:
            print(f"  ⚠️ 草稿缺少 task_id，跳过")
            return {"success": False, "message": "草稿缺少 task_id"}
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查找绑定了这个 sora_task_id 的任务
        cursor.execute("""
            SELECT id, prompt, status, video_url
            FROM tasks
            WHERE sora_task_id = %s
        """, (sora_task_id,))
        
        task = cursor.fetchone()
        
        if task:
            task_id = task['id']
            task_prompt = task['prompt']
            task_status = task['status']
            task_video_url = task['video_url']
            print(f"  📌 找到绑定的任务: ID={task_id}")
            
            # 不再保存草稿URL到video_url字段
            # video_url字段应该保存视频文件的下载URL，而不是草稿页面URL
            # 草稿URL是临时的，最终需要的是permalink（发布后的URL）
            
            # 只更新任务状态为success，但不更新video_url
            if task_status != 'success':
                cursor.execute("""
                    UPDATE tasks
                    SET status = 'success',
                        end_time = %s,
                        progress = 100,
                        progress_message = 'completed'
                    WHERE id = %s
                """, (datetime.now().isoformat(), task_id))
                
                print(f"  ✅ 任务 {task_id} 状态已更新为 success")
                print(f"  ℹ️ 草稿URL不保存到video_url，等待发布后获取permalink")
            else:
                print(f"  ℹ️ 任务 {task_id} 已是success状态")
        else:
            # 未找到绑定的任务，尝试通过提示词匹配并绑定
            print(f"  ⚠️ 未找到绑定的任务，尝试通过提示词匹配...")
            
            if prompt:
                # 构造草稿页面 URL
                draft_url = f"https://sora.chatgpt.com/d/{draft_id}"
                
                # 先尝试精确匹配（只取第一个匹配的任务，实现去重）
                cursor.execute("""
                    SELECT id, prompt, status
                    FROM tasks
                    WHERE status IN ('running', 'pending', 'success')
                    AND sora_task_id IS NULL
                    AND TRIM(prompt) = %s
                    ORDER BY 
                        CASE 
                            WHEN status = 'running' THEN 0 
                            WHEN status = 'pending' THEN 1
                            WHEN status = 'success' THEN 2
                            ELSE 3
                        END,
                        id DESC
                    LIMIT 1
                """, (prompt.strip(),))
                
                exact_match = cursor.fetchone()
                matched_task_id = None
                
                if exact_match:
                    task_id = exact_match['id']
                    task_prompt = exact_match['prompt']
                    task_status = exact_match['status']
                    print(f"  ✅ 精确匹配成功！任务ID: {task_id}")
                    print(f"     提示词: {task_prompt[:50]}...")
                    
                    # 更新任务的 sora_task_id，但不保存草稿URL到video_url
                    update_sql = """
                        UPDATE tasks 
                        SET sora_task_id = %s,
                            status = 'success',
                            end_time = %s,
                            progress = 100,
                            progress_message = 'completed'
                        WHERE id = %s
                    """
                    
                    cursor.execute(update_sql, (sora_task_id, datetime.now().isoformat(), task_id))
                    matched_task_id = task_id
                    
                    print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                    print(f"  ℹ️ 草稿URL不保存，等待发布后获取permalink")
                else:
                    # 如果没有精确匹配，尝试模糊匹配（也只取第一个）
                    print(f"  ⚠️ 未找到精确匹配，尝试模糊匹配...")
                    
                    cursor.execute("""
                        SELECT id, prompt, status
                        FROM tasks
                        WHERE status IN ('running', 'pending', 'success')
                        AND sora_task_id IS NULL
                        AND prompt IS NOT NULL
                        ORDER BY 
                            CASE 
                                WHEN status = 'running' THEN 0 
                                WHEN status = 'pending' THEN 1
                                WHEN status = 'success' THEN 2
                                ELSE 3
                            END,
                            id DESC
                    """)
                    
                    tasks = cursor.fetchall()
                    prompt_clean = prompt.strip().lower()
                    
                    # 遍历查找模糊匹配（只匹配第一个）
                    for task_row in tasks:
                        task_id = task_row['id']
                        task_prompt = task_row['prompt']
                        task_status = task_row['status']
                        if task_prompt:
                            task_prompt_clean = task_prompt.strip().lower()
                            
                            if task_prompt_clean in prompt_clean or prompt_clean in task_prompt_clean:
                                print(f"  ✅ 模糊匹配成功！任务ID: {task_id}")
                                print(f"     任务提示词: {task_prompt[:50]}...")
                                print(f"     草稿提示词: {prompt[:50]}...")
                                
                                # 更新任务的 sora_task_id，但不保存草稿URL到video_url
                                update_sql = """
                                    UPDATE tasks 
                                    SET sora_task_id = %s,
                                        status = 'success',
                                        end_time = %s,
                                        progress = 100,
                                        progress_message = 'completed'
                                    WHERE id = %s
                                """
                                
                                cursor.execute(update_sql, (sora_task_id, datetime.now().isoformat(), task_id))
                                matched_task_id = task_id
                                
                                print(f"  ✅ 任务 {task_id} 已绑定 Sora 任务ID: {sora_task_id}")
                                print(f"  ℹ️ 草稿URL不保存，等待发布后获取permalink")
                                
                                break
                    
                    if not matched_task_id:
                        print(f"  ⚠️ 未找到匹配的任务")
            else:
                print(f"  ⚠️ 没有提示词，无法匹配任务")
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 草稿处理完成\n")
        return {"success": True, "message": "草稿已处理"}
        
    except Exception as e:
        print(f"  ❌ 处理失败: {e}\n")
        import traceback
        traceback.print_exc()
        raise

# 处理已发布视频
async def handle_published_video(data: dict):
    """
    处理已发布视频信息
    
    已发布视频数据包含:
    - post_id: 发布ID (s_xxx)
    - permalink: 发布链接 (https://sora.chatgpt.com/p/s_xxx)
    - text: 发布文本
    - discovery_phrase: 发现短语
    - attachments: 附件信息（包含 generation_id, task_id）
    - 统计信息: like_count, view_count 等
    """
    try:
        post_id = data.get('post_id')
        permalink = data.get('permalink')
        
        # 如果没有permalink，用post_id拼接
        if not permalink and post_id:
            permalink = f"https://sora.chatgpt.com/p/{post_id}"
            print(f"  ⚠️ 未提供permalink，已自动拼接: {permalink}")
        
        text = data.get('text')
        discovery_phrase = data.get('discovery_phrase')
        attachments = data.get('attachments', [])
        
        print(f"  Post ID: {post_id}")
        print(f"  Permalink: {permalink}")
        print(f"  文本: {text or '(无)'}")
        print(f"  发现短语: {discovery_phrase or '(无)'}")
        print(f"  观看次数: {data.get('view_count', 0)}")
        
        # 提取附件中的 generation_id 和 task_id
        generation_id = None
        sora_task_id = None
        
        if attachments and len(attachments) > 0:
            attachment = attachments[0]
            generation_id = attachment.get('generation_id')
            sora_task_id = attachment.get('task_id')
            
            if generation_id:
                print(f"  Generation ID: {generation_id}")
            if sora_task_id:
                print(f"  Sora Task ID: {sora_task_id}")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 方法 1: 通过 sora_task_id 查找任务
        if sora_task_id:
            cursor.execute("""
                SELECT id, prompt, status, video_url
                FROM tasks
                WHERE sora_task_id = %s
            """, (sora_task_id,))
            
            task = cursor.fetchone()
            
            if task:
                task_id = task['id']
                prompt = task['prompt']
                status = task['status']
                video_url = task['video_url']
                print(f"  📌 找到绑定的任务: ID={task_id}")
                
                # 更新任务的发布信息
                cursor.execute("""
                    UPDATE tasks
                    SET post_id = %s,
                        permalink = %s,
                        posted_at = %s,
                        is_published = 1,
                        status = 'published'
                    WHERE id = %s
                """, (post_id, permalink, data.get('posted_at'), task_id))
                
                conn.commit()
                print(f"  ✅ 任务 {task_id} 已更新为已发布状态")
                print(f"  ✅ Permalink: {permalink}")
                
                # 🆕 释放窗口：任务真正完成了
                if task['profile_id']:
                    profile_id = task['profile_id']
                    with window_manager.lock:
                        if profile_id in window_manager.window_status:
                            window_manager.window_status[profile_id] = {
                                'status': 'idle',
                                'current_task_id': None
                            }
                    print(f"  ✅ 窗口 {profile_id} 已释放（任务已发布）")
            else:
                print(f"  ⚠️ 未找到绑定的任务 (sora_task_id={sora_task_id})")
        
        # 方法 2: 保存到 draft_post_binding 表（如果有 generation_id）
        if generation_id and post_id:
            # 确保表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS draft_post_binding (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    draft_id VARCHAR(255) NOT NULL,
                    generation_id VARCHAR(255),
                    task_id VARCHAR(255),
                    draft_url TEXT,
                    post_id VARCHAR(255) NOT NULL,
                    published_url TEXT NOT NULL,
                    created_at VARCHAR(255) NOT NULL,
                    UNIQUE KEY unique_draft (draft_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 插入或更新绑定关系
            draft_url = f"https://sora.chatgpt.com/d/{generation_id}"
            
            cursor.execute("""
                INSERT INTO draft_post_binding
                (draft_id, generation_id, task_id, draft_url, post_id, published_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    generation_id = VALUES(generation_id),
                    task_id = VALUES(task_id),
                    draft_url = VALUES(draft_url),
                    post_id = VALUES(post_id),
                    published_url = VALUES(published_url),
                    created_at = VALUES(created_at)
            """, (generation_id, generation_id, sora_task_id, draft_url, post_id, permalink, 
                  data.get('captured_at') or datetime.now().isoformat()))
            
            conn.commit()
            print(f"  ✅ 绑定关系已保存: {generation_id} → {post_id}")
        
        conn.close()
        
        print(f"  ✅ 已发布视频处理完成\n")
        return {"success": True, "message": "已发布视频已处理"}
        
    except Exception as e:
        print(f"  ❌ 处理失败: {e}\n")
        import traceback
        traceback.print_exc()
        raise

# ==================== 视频抓包接口 ====================

class VideoCaptureData(BaseModel):
    post_id: str
    text: Optional[str] = None
    caption: Optional[str] = None
    posted_at: Optional[float] = None
    updated_at: Optional[float] = None
    permalink: Optional[str] = None
    share_ref: Optional[str] = None
    like_count: Optional[int] = 0
    view_count: Optional[int] = 0
    unique_view_count: Optional[int] = 0
    remix_count: Optional[int] = 0
    reply_count: Optional[int] = 0
    user_id: Optional[str] = None
    username: Optional[str] = None
    profile_picture_url: Optional[str] = None
    verified: Optional[bool] = False
    generation_id: Optional[str] = None
    task_id: Optional[str] = None
    video_url: Optional[str] = None
    downloadable_url: Optional[str] = None
    download_url_watermark: Optional[str] = None
    download_url_no_watermark: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    n_frames: Optional[int] = None
    prompt: Optional[str] = None
    source_url: Optional[str] = None
    source_size: Optional[int] = None
    thumbnail_url: Optional[str] = None
    md_url: Optional[str] = None
    ld_url: Optional[str] = None
    gif_url: Optional[str] = None
    emoji: Optional[str] = None
    discovery_phrase: Optional[str] = None
    source: Optional[str] = None
    captured_at: Optional[str] = None

@app.post("/api/videos/capture")
async def capture_video(data: VideoCaptureData):
    """
    接收插件抓包的视频数据
    
    数据来源: plug-renwu 插件
    """
    try:
        # 如果没有permalink，用post_id拼接
        if not data.permalink and data.post_id:
            data.permalink = f"https://sora.chatgpt.com/p/{data.post_id}"
        
        print("\n" + "="*80)
        print("[视频抓包] 收到新的视频数据")
        print(f"  帖子ID: {data.post_id}")
        if data.permalink:
            print(f"  Permalink: {data.permalink}")
        print(f"  用户: {data.username} ({data.user_id})")
        print(f"  文本: {data.text or data.prompt}")
        print(f"  视频URL: {data.video_url}")
        print(f"  下载URL: {data.downloadable_url}")
        print(f"  尺寸: {data.width}x{data.height}")
        print(f"  帧数: {data.n_frames}")
        print(f"  观看数: {data.view_count}")
        print(f"  点赞数: {data.like_count}")
        print("="*80 + "\n")
        
        # 保存到数据库
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM captured_videos WHERE post_id = %s", (data.post_id,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE captured_videos SET
                    text = %s, caption = %s, posted_at = %s, updated_at = %s,
                    permalink = %s, share_ref = %s, like_count = %s, view_count = %s,
                    unique_view_count = %s, remix_count = %s, reply_count = %s,
                    user_id = %s, username = %s, profile_picture_url = %s, verified = %s,
                    generation_id = %s, task_id = %s, video_url = %s, downloadable_url = %s,
                    download_url_watermark = %s, download_url_no_watermark = %s,
                    width = %s, height = %s, n_frames = %s, prompt = %s,
                    source_url = %s, source_size = %s, thumbnail_url = %s,
                    md_url = %s, ld_url = %s, gif_url = %s,
                    emoji = %s, discovery_phrase = %s, source = %s,
                    last_captured_at = %s
                WHERE post_id = %s
            """, (
                data.text, data.caption, data.posted_at, data.updated_at,
                data.permalink, data.share_ref, data.like_count, data.view_count,
                data.unique_view_count, data.remix_count, data.reply_count,
                data.user_id, data.username, data.profile_picture_url, data.verified,
                data.generation_id, data.task_id, data.video_url, data.downloadable_url,
                data.download_url_watermark, data.download_url_no_watermark,
                data.width, data.height, data.n_frames, data.prompt,
                data.source_url, data.source_size, data.thumbnail_url,
                data.md_url, data.ld_url, data.gif_url,
                data.emoji, data.discovery_phrase, data.source,
                data.captured_at or datetime.now().isoformat(),
                data.post_id
            ))
            video_id = existing['id']
            message = "视频信息已更新"
            print(f"  ✅ 更新现有视频记录 ID: {video_id}")
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO captured_videos (
                    post_id, text, caption, posted_at, updated_at,
                    permalink, share_ref, like_count, view_count,
                    unique_view_count, remix_count, reply_count,
                    user_id, username, profile_picture_url, verified,
                    generation_id, task_id, video_url, downloadable_url,
                    download_url_watermark, download_url_no_watermark,
                    width, height, n_frames, prompt,
                    source_url, source_size, thumbnail_url,
                    md_url, ld_url, gif_url,
                    emoji, discovery_phrase, source,
                    captured_at, last_captured_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.post_id, data.text, data.caption, data.posted_at, data.updated_at,
                data.permalink, data.share_ref, data.like_count, data.view_count,
                data.unique_view_count, data.remix_count, data.reply_count,
                data.user_id, data.username, data.profile_picture_url, data.verified,
                data.generation_id, data.task_id, data.video_url, data.downloadable_url,
                data.download_url_watermark, data.download_url_no_watermark,
                data.width, data.height, data.n_frames, data.prompt,
                data.source_url, data.source_size, data.thumbnail_url,
                data.md_url, data.ld_url, data.gif_url,
                data.emoji, data.discovery_phrase, data.source,
                data.captured_at or datetime.now().isoformat(),
                data.captured_at or datetime.now().isoformat()
            ))
            video_id = cursor.lastrowid
            message = "视频信息已保存"
            print(f"  ✅ 新增视频记录 ID: {video_id}")
        
        conn.commit()
        conn.close()
        
        # 🆕 同步到 sora_videos 表（前端显示的表）
        try:
            print(f"  🔄 同步到 sora_videos 表...")
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 确定账号邮箱
            account_email = None
            if data.user_id:
                # 从 sora_accounts 表查找账号
                cursor.execute("SELECT email FROM sora_accounts WHERE user_id = %s", (data.user_id,))
                account_row = cursor.fetchone()
                if account_row:
                    account_email = account_row['email']
                    print(f"     找到账号: {account_email}")
            
            if not account_email:
                # 如果没有找到，使用用户名作为临时邮箱
                account_email = f"{data.username}@temp.local"
                print(f"     使用临时邮箱: {account_email}")
            
            # 检查是否已存在（使用 video_id 字段）
            cursor.execute("SELECT id, status FROM sora_videos WHERE video_id = %s", (data.post_id,))
            existing_video = cursor.fetchone()
            
            if existing_video:
                # 更新现有记录
                cursor.execute("""
                    UPDATE sora_videos
                    SET url = %s,
                        status = 'published',
                        source = %s,
                        progress = 100,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE video_id = %s
                """, (data.permalink or f"https://sora.chatgpt.com/p/{data.post_id}",
                      data.source,
                      data.post_id))
                print(f"     ✅ 更新 sora_videos 记录: {data.post_id}")
            else:
                # 插入新记录（注意：id 是自增的，video_id 存储 post_id）
                cursor.execute("""
                    INSERT INTO sora_videos (
                        video_id, account_email, url, status, source, progress,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    data.post_id,  # video_id 字段
                    account_email,
                    data.permalink or f"https://sora.chatgpt.com/p/{data.post_id}",
                    'published',
                    data.source,
                    100
                ))
                print(f"     ✅ 新增 sora_videos 记录: {data.post_id}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"     ⚠️ 同步到 sora_videos 失败: {e}")
            import traceback
            traceback.print_exc()
            # 确保关闭连接
            try:
                conn.close()
            except:
                pass
        
        # 🆕 如果有task_id或generation_id，更新tasks表
        if data.task_id or data.generation_id:
            try:
                print(f"  🔍 尝试更新任务...")
                print(f"     task_id: {data.task_id}")
                print(f"     generation_id: {data.generation_id}")
                
                # 重用已有的连接
                conn = db.get_connection()
                cursor = conn.cursor()
                
                # 通过task_id或generation_id查找任务
                if data.task_id:
                    print(f"  🔍 通过 sora_task_id 查找: {data.task_id}")
                    cursor.execute("""
                        SELECT id, status, permalink, profile_id
                        FROM tasks
                        WHERE sora_task_id = %s
                    """, (data.task_id,))
                elif data.generation_id:
                    print(f"  🔍 通过 generation_id 查找: {data.generation_id}")
                    cursor.execute("""
                        SELECT id, status, permalink, profile_id
                        FROM tasks
                        WHERE generation_id = %s
                    """, (data.generation_id,))
                
                task = cursor.fetchone()
                
                if task:
                    task_id = task['id']
                    task_status = task['status']
                    task_permalink = task['permalink']
                    profile_id = task['profile_id']
                    print(f"  📌 找到关联任务: ID={task_id}, 当前状态={task_status}")
                    
                    # 更新任务的发布信息
                    cursor.execute("""
                        UPDATE tasks
                        SET post_id = %s,
                            permalink = %s,
                            video_url = %s,
                            is_published = 1,
                            status = 'published',
                            posted_at = %s
                        WHERE id = %s
                    """, (data.post_id, data.permalink, data.downloadable_url or data.video_url,
                          data.posted_at, task_id))
                    
                    conn.commit()
                    print(f"  ✅ 任务 {task_id} 已更新: running → published")
                    print(f"  ✅ Permalink: {data.permalink}")
                    
                    # 🆕 从草稿队列中移除（如果存在）
                    if data.generation_id:
                        global draft_queue
                        original_length = len(draft_queue)
                        draft_queue = [d for d in draft_queue if d.get('draft_id') != data.generation_id and d.get('generation_id') != data.generation_id]
                        removed = original_length - len(draft_queue)
                        if removed > 0:
                            print(f"  ✅ 已从草稿队列移除: {data.generation_id}")
                    
                    # 释放窗口
                    if profile_id:
                        with window_manager.lock:
                            if profile_id in window_manager.window_status:
                                old_status = window_manager.window_status[profile_id]['status']
                                window_manager.window_status[profile_id] = {
                                    'status': 'idle',
                                    'current_task_id': None
                                }
                                print(f"  ✅ 窗口 {profile_id} 已释放: {old_status} → idle")
                            else:
                                print(f"  ⚠️ 窗口 {profile_id} 不在管理器中")
                    else:
                        print(f"  ⚠️ 任务 {task_id} 没有关联窗口")
                else:
                    print(f"  ⚠️ 未找到关联任务")
                    print(f"     task_id={data.task_id}")
                    print(f"     generation_id={data.generation_id}")
                    
                    # 尝试查看数据库中有哪些任务
                    cursor.execute("""
                        SELECT id, sora_task_id, generation_id, status, prompt
                        FROM tasks
                        WHERE status IN ('running', 'success')
                        LIMIT 5
                    """)
                    running_tasks = cursor.fetchall()
                    print(f"  📋 当前运行中/成功的任务:")
                    for rt in running_tasks:
                        print(f"     ID={rt['id']}, sora_task_id={rt['sora_task_id']}, generation_id={rt['generation_id']}, status={rt['status']}, prompt={rt['prompt'][:30] if rt['prompt'] else 'N/A'}...")
                
                conn.close()
            except Exception as e:
                print(f"  ⚠️ 更新任务失败: {e}")
                import traceback
                traceback.print_exc()
                # 确保关闭连接
                try:
                    conn.close()
                except:
                    pass
        
        # 尝试匹配任务（如果有提示词但没有task_id）
        matched_task = None
        if not data.task_id and not data.generation_id and (data.prompt or data.text):
            prompt_to_match = data.prompt or data.text
            try:
                match_result = await match_task_by_prompt({
                    'prompt': prompt_to_match,
                    'video_url': data.downloadable_url or data.video_url
                })
                if match_result.get('success'):
                    matched_task = match_result.get('task_id')
                    print(f"  ✅ 已匹配到任务 ID: {matched_task}")
            except Exception as e:
                print(f"  ⚠️ 任务匹配失败: {e}")
        
        return {
            "success": True,
            "message": message,
            "video_id": video_id,
            "matched_task_id": matched_task
        }
        
    except Exception as e:
        print(f"[视频抓包] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/captured")
async def get_captured_videos(
    limit: int = 50,
    offset: int = 0,
    username: Optional[str] = None
):
    """获取抓包的视频列表"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 构建查询
        query = "SELECT * FROM captured_videos"
        params = []
        
        if username:
            query += " WHERE username = %s"
            params.append(username)
        
        query += " ORDER BY last_captured_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        videos = cursor.fetchall()
        
        # 获取总数
        count_query = "SELECT COUNT(*) as count FROM captured_videos"
        if username:
            count_query += " WHERE username = %s"
            cursor.execute(count_query, [username])
        else:
            cursor.execute(count_query)
        
        total = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "success": True,
            "data": videos,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"[获取抓包视频] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/captured/{video_id}")
async def get_captured_video(video_id: int):
    """获取单个抓包视频详情"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM captured_videos WHERE id = %s", (video_id,))
        video = cursor.fetchone()
        
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        conn.close()
        
        return {
            "success": True,
            "data": video
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[获取视频详情] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/videos/captured/{video_id}")
async def delete_captured_video(video_id: int):
    """删除抓包的视频"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM captured_videos WHERE id = %s", (video_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "视频已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[删除视频] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/captured/stats")
async def get_captured_videos_stats():
    """获取抓包视频统计信息"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 总数
        cursor.execute("SELECT COUNT(*) as count FROM captured_videos")
        total = cursor.fetchone()['count']
        
        # 按用户统计
        cursor.execute("""
            SELECT username, COUNT(*) as count
            FROM captured_videos
            GROUP BY username
            ORDER BY count DESC
            LIMIT 10
        """)
        by_user = [{"username": row['username'], "count": row['count']} for row in cursor.fetchall()]
        
        # 今日新增
        cursor.execute("""
            SELECT COUNT(*) as count FROM captured_videos
            WHERE DATE(last_captured_at) = CURDATE()
        """)
        today = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "total": total,
                "today": today,
                "by_user": by_user
            }
        }
        
    except Exception as e:
        print(f"[获取统计信息] 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/videos/{video_id}/prompt")
async def update_video_prompt(video_id: str, data: dict):
    """更新视频的提示词"""
    try:
        prompt = data.get('prompt')
        url = data.get('url')
        
        print(f"\n[更新提示词] 视频ID: {video_id}")
        print(f"  提示词: {prompt}")
        print(f"  URL: {url}")
        
        # 更新数据库中的提示词
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 更新 sora_videos 表
        cursor.execute("""
            UPDATE sora_videos 
            SET prompt = %s, updated_at = CURRENT_TIMESTAMP
            WHERE video_id = %s
        """, (prompt, video_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"  ✅ 数据库已更新 ({affected} 行)\n")
            return {"success": True, "message": "提示词已更新"}
        else:
            print(f"  ⚠️ 未找到视频ID: {video_id}\n")
            return {"success": False, "message": "视频不存在"}
        
    except Exception as e:
        print(f"[更新提示词] 失败: {e}\n")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

# ==================== 系统配置 ====================

@app.get("/api/config")
async def get_config():
    """获取系统配置"""
    try:
        return {
            "success": True,
            "data": {
                "auto_close_windows_on_shutdown": config.AUTO_CLOSE_WINDOWS_ON_SHUTDOWN,
                "auto_detect_open_windows_on_startup": config.AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(config_update: ConfigUpdate):
    """更新系统配置"""
    try:
        if config_update.auto_close_windows_on_shutdown is not None:
            config.AUTO_CLOSE_WINDOWS_ON_SHUTDOWN = config_update.auto_close_windows_on_shutdown
        
        if config_update.auto_detect_open_windows_on_startup is not None:
            config.AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP = config_update.auto_detect_open_windows_on_startup
        
        return {
            "success": True,
            "message": "配置已更新",
            "data": {
                "auto_close_windows_on_shutdown": config.AUTO_CLOSE_WINDOWS_ON_SHUTDOWN,
                "auto_detect_open_windows_on_startup": config.AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 对外API - 视频任务管理 ====================

@app.post("/v1/videos")
async def create_video_task(request: VideoCreateRequest, authorization: str = Header(None)):
    """
    创建视频生成任务（对外API）
    
    需要 Authorization 头: Bearer OtEsP8DOVH0lRvWxxIS4PvTCsl6wsAVh
    
    参数:
    - id: 任务ID（可选，不指定则自动生成）
    - prompt: 提示词（必填）
    - image: 图片URL（可选）
    - model: 模型名称（可选）
    
    返回:
    {
        "id": 123,
        "status": "pending",
        "message": "任务创建成功"
    }
    """
    # 验证 API 密钥
    verify_api_key(authorization)
    
    try:
        # 创建任务
        task_id = db.create_task(
            prompt=request.prompt,
            image=request.image,
            model=request.model,
            task_id=request.id
        )
        
        return {
            "id": task_id,
            "status": "pending",
            "message": "任务创建成功"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/v1/videos/{video_id}")
async def get_video_progress(video_id: str, authorization: str = Header(None)):
    """
    查询视频生成进度（对外API）
    
    需要 Authorization 头: Bearer OtEsP8DOVH0lRvWxxIS4PvTCsl6wsAVh
    
    格式兼容: https://api.dyuapi.com/v1/videos/video_xxx
    
    返回格式:
    {
        "id": "video_xxx",
        "object": "video",
        "status": "pending|processing|completed|failed",
        "progress": 0-100,
        "progress_message": "当前状态描述",
        "video_url": "视频URL（完成时）",
        "created_at": 时间戳,
        "completed_at": 时间戳（完成时）
    }
    """
    # 验证 API 密钥
    verify_api_key(authorization)
    
    try:
        # 从video_id中提取任务ID（格式: video_123 或 task_123）
        task_id = None
        if video_id.startswith('video_'):
            task_id = int(video_id.replace('video_', ''))
        elif video_id.startswith('task_'):
            task_id = int(video_id.replace('task_', ''))
        else:
            # 尝试直接解析为数字
            try:
                task_id = int(video_id)
            except:
                raise HTTPException(status_code=400, detail="Invalid video_id format")
        
        # 查询任务
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # 转换状态为标准格式
        status_map = {
            'pending': 'pending',
            'running': 'processing',
            'success': 'completed',
            'published': 'completed',  # 🆕 已发布也算完成
            'failed': 'failed',
            'publish_failed': 'failed'  # 🆕 发布失败也算失败
        }
        
        # 构建响应
        response = {
            "id": f"video_{task_id}",
            "object": "video",
            "status": status_map.get(task['status'], 'pending'),
            "progress": task.get('progress', 0) if task['status'] not in ['success', 'published'] else 100
        }
        
        # 添加进度消息
        if task.get('progress_message'):
            response['progress_message'] = task['progress_message']
        
        # 添加视频URL（如果已完成）
        if task['status'] in ['success', 'published']:
            # 🆕 转换为CDN直链
            video_url = None
            
            # 优先使用发布链接
            if task.get('permalink'):
                # 从 permalink 提取 post_id
                # 格式: https://sora.chatgpt.com/p/s_xxxxx
                import re
                match = re.search(r'/p/(s_[a-f0-9]+)', task['permalink'])
                if match:
                    post_id = match.group(1)
                    # 转换为CDN链接
                    video_url = f"https://oscdn2.dyysy.com/MP4/{post_id}.mp4"
                    response['is_published'] = True
                else:
                    # 如果无法提取，使用原链接
                    video_url = task['permalink']
                    response['is_published'] = True
            elif task.get('video_url'):
                # 如果只有草稿链接，也尝试提取generation_id
                # 格式: https://videos.openai.com/az/files/00000000-xxxx-xxxx-xxxx-xxxxxxxxxxxx/raw?...
                # 或: https://sora.chatgpt.com/d/gen_xxxxx
                if 'sora.chatgpt.com/d/' in task['video_url']:
                    match = re.search(r'/d/(gen_[a-f0-9]+)', task['video_url'])
                    if match:
                        generation_id = match.group(1)
                        # 草稿链接暂时保持原样（因为没有对应的CDN链接）
                        video_url = task['video_url']
                else:
                    video_url = task['video_url']
                response['is_published'] = False
            
            if video_url:
                response['video_url'] = video_url
            
            response['completed_at'] = task.get('end_time') or task.get('posted_at')
        
        # 添加创建时间
        if task.get('created_at'):
            response['created_at'] = task['created_at']
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 草稿队列管理 ====================

# 内存中的草稿队列
draft_queue = []
draft_queue_lock = None

@app.post("/api/drafts/queue")
async def add_to_draft_queue(data: dict):
    """
    接收 plug-renwu 发送的未发布草稿队列
    
    数据格式:
    {
        "drafts": [
            {
                "draft_id": "gen_xxx",
                "generation_id": "gen_xxx",
                "task_id": "task_xxx",
                "prompt": "提示词",
                "draft_url": "https://sora.chatgpt.com/d/gen_xxx",
                "thumbnail_url": "..."
            }
        ],
        "timestamp": "2026-02-04T10:30:00.000Z"
    }
    """
    global draft_queue
    
    try:
        drafts = data.get('drafts', [])
        timestamp = data.get('timestamp')
        
        print(f"\n{'='*80}")
        print(f"[草稿队列] 收到 {len(drafts)} 个未发布草稿")
        print(f"{'='*80}")
        print(f"  时间: {timestamp}")
        
        # 清空旧队列，使用新队列
        draft_queue = []
        
        for draft in drafts:
            draft_id = draft.get('draft_id')
            task_id = draft.get('task_id')
            prompt = draft.get('prompt', '')
            
            # 检查是否已在队列中
            if not any(d.get('draft_id') == draft_id for d in draft_queue):
                draft_queue.append(draft)
                print(f"  ➕ {draft_id} - {prompt[:50]}...")
        
        print(f"\n  📋 当前队列长度: {len(draft_queue)}")
        print(f"{'='*80}\n")
        
        return {
            "success": True,
            "message": f"已添加 {len(draft_queue)} 个草稿到队列",
            "queue_length": len(draft_queue)
        }
        
    except Exception as e:
        print(f"[草稿队列] 添加失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drafts/queue")
async def get_draft_queue():
    """
    获取当前的草稿队列
    plug-in 通过此接口获取待发布的草稿
    """
    try:
        print(f"\n[草稿队列] plug-in 请求队列，当前长度: {len(draft_queue)}")
        
        return {
            "success": True,
            "drafts": draft_queue,
            "queue_length": len(draft_queue),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[草稿队列] 获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/drafts/queue/{draft_id}")
async def remove_from_draft_queue(draft_id: str):
    """
    从队列中移除已处理的草稿
    """
    global draft_queue
    
    try:
        original_length = len(draft_queue)
        draft_queue = [d for d in draft_queue if d.get('draft_id') != draft_id]
        removed = original_length - len(draft_queue)
        
        if removed > 0:
            print(f"[草稿队列] 已移除: {draft_id}, 剩余: {len(draft_queue)}")
            return {
                "success": True,
                "message": f"已移除草稿 {draft_id}",
                "queue_length": len(draft_queue)
            }
        else:
            return {
                "success": False,
                "message": f"草稿 {draft_id} 不在队列中",
                "queue_length": len(draft_queue)
            }
        
    except Exception as e:
        print(f"[草稿队列] 移除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drafts/queue/clear")
async def clear_draft_queue():
    """
    清空草稿队列
    """
    global draft_queue
    
    try:
        count = len(draft_queue)
        draft_queue = []
        
        print(f"[草稿队列] 已清空，移除了 {count} 个草稿")
        
        return {
            "success": True,
            "message": f"已清空队列，移除了 {count} 个草稿",
            "queue_length": 0
        }
        
    except Exception as e:
        print(f"[草稿队列] 清空失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 图片代理接口 ====================

@app.get("/api/image-proxy")
async def image_proxy(url: str):
    """
    图片代理接口，解决跨域问题
    """
    try:
        import requests
        from fastapi.responses import Response
        
        # 下载图片
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code == 200:
            # 返回图片内容
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=86400',  # 缓存1天
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            raise HTTPException(status_code=response.status_code, detail="图片加载失败")
            
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"图片加载失败: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("=" * 60)
    print("Sora 自动化管理系统")
    print("=" * 60)
    print(f"服务地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print(f"健康检查: http://localhost:8000/health")
    print(f"管理接口: http://localhost:8000/api/*")
    print(f"公开接口: http://localhost:8000/v1/*")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


# ==================== 自动发布相关接口 ====================

@app.get("/api/drafts/unpublished")
async def get_unpublished_drafts():
    """
    获取未发布的草稿列表（用于 plug-in 自动发布）
    返回包含 task_id 和 draft_url 的草稿列表
    """
    try:
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 查询未发布的草稿
        # 条件：有 sora_task_id，有 video_url（草稿URL），但没有 permalink（发布URL）
        cursor.execute("""
            SELECT 
                id,
                sora_task_id,
                prompt,
                video_url,
                status
            FROM tasks
            WHERE sora_task_id IS NOT NULL
            AND video_url IS NOT NULL
            AND video_url LIKE '%/d/gen_%'
            AND (permalink IS NULL OR permalink = '')
            AND (is_published IS NULL OR is_published = 0)
            ORDER BY id ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        drafts = []
        for row in rows:
            task_id = row['id']
            sora_task_id = row['sora_task_id']
            prompt = row['prompt']
            video_url = row['video_url']
            status = row['status']
            drafts.append({
                "task_id": task_id,
                "sora_task_id": sora_task_id,
                "prompt": prompt,
                "draft_url": video_url,
                "status": status
            })
        
        print(f"\n[获取未发布草稿] 找到 {len(drafts)} 个未发布草稿")
        for draft in drafts:
            print(f"  - 任务 {draft['task_id']}: {draft['prompt'][:50] if draft['prompt'] else 'No prompt'}...")
        
        return {
            "success": True,
            "count": len(drafts),
            "drafts": drafts
        }
        
    except Exception as e:
        print(f"[获取未发布草稿] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/drafts/publish-result")
async def receive_publish_result(data: dict):
    """
    接收 plug-in 发布结果的回调
    更新任务的发布状态和 URL
    """
    try:
        task_id = data.get('task_id')
        published_url = data.get('published_url')
        success = data.get('success')
        error = data.get('error')
        
        if not task_id:
            raise HTTPException(status_code=400, detail="缺少 task_id")
        
        print(f"\n[发布结果回调] 任务 {task_id}")
        print(f"  成功: {success}")
        print(f"  发布URL: {published_url}")
        if error:
            print(f"  错误: {error}")
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if success and published_url:
            # 发布成功，更新任务
            cursor.execute("""
                UPDATE tasks
                SET permalink = %s,
                    is_published = 1,
                    posted_at = %s,
                    status = 'published'
                WHERE id = %s
            """, (published_url, datetime.now().isoformat(), task_id))
            
            print(f"  ✅ 任务 {task_id} 已标记为已发布")
            print(f"  ✅ 发布URL: {published_url}")
        else:
            # 发布失败，记录错误
            cursor.execute("""
                UPDATE tasks
                SET status = 'publish_failed'
                WHERE id = %s
            """, (task_id,))
            
            print(f"  ❌ 任务 {task_id} 发布失败: {error}")
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "发布结果已记录"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[发布结果回调] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/publish/result")
async def receive_plugin_publish_result(data: dict):
    """
    接收 plug-in 插件的发布结果
    建立 draft_id 和 post_id 的绑定关系
    
    数据格式:
    {
        "draft_id": "gen_xxx",           # 未发布草稿 ID
        "generation_id": "gen_xxx",      # 生成 ID
        "task_id": "task_xxx",           # Sora 任务 ID
        "draft_url": "https://sora.chatgpt.com/d/gen_xxx",
        "published_url": "https://sora.chatgpt.com/p/s_xxx",
        "post_id": "s_xxx",              # 已发布视频 ID
        "success": true,
        "timestamp": "2026-02-04T10:30:00.000Z"
    }
    """
    try:
        draft_id = data.get('draft_id')
        generation_id = data.get('generation_id')
        task_id = data.get('task_id')
        draft_url = data.get('draft_url')
        published_url = data.get('published_url')
        post_id = data.get('post_id')
        success = data.get('success')
        timestamp = data.get('timestamp')
        
        print(f"\n{'='*80}")
        print(f"[Plug-in 发布结果]")
        print(f"{'='*80}")
        print(f"  草稿 ID: {draft_id}")
        print(f"  生成 ID: {generation_id}")
        print(f"  任务 ID: {task_id}")
        print(f"  草稿 URL: {draft_url}")
        print(f"  发布 URL: {published_url}")
        print(f"  Post ID: {post_id}")
        print(f"  成功: {success}")
        print(f"  时间: {timestamp}")
        print(f"{'='*80}")
        
        if not draft_id:
            raise HTTPException(status_code=400, detail="缺少 draft_id")
        
        if not success:
            print(f"  ⚠️ 发布失败，不更新数据库")
            return {
                "success": True,
                "message": "发布失败已记录"
            }
        
        if not post_id or not published_url:
            raise HTTPException(status_code=400, detail="发布成功但缺少 post_id 或 published_url")
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # 🆕 步骤 1: 同步更新 sora_videos 表（前端显示的数据来源）
        # 查找草稿记录（draft_id 或 generation_id）
        cursor.execute("""
            SELECT id, account_email, prompt, url, status
            FROM sora_videos
            WHERE id = %s OR id = %s
        """, (draft_id, generation_id))
        
        video_record = cursor.fetchone()
        
        if video_record:
            video_id = video_record['id']
            account_email = video_record['account_email']
            prompt = video_record['prompt']
            old_url = video_record['url']
            old_status = video_record['status']
            print(f"  ✅ 在 sora_videos 表中找到草稿记录")
            print(f"     视频 ID: {video_id}")
            print(f"     账号: {account_email}")
            print(f"     原状态: {old_status}")
            print(f"     原 URL: {old_url}")
            
            # 更新为已发布状态
            cursor.execute("""
                UPDATE sora_videos
                SET url = %s,
                    status = 'published',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (published_url, video_id))
            
            print(f"  ✅ sora_videos 表已更新")
            print(f"     新状态: published")
            print(f"     新 URL: {published_url}")
        else:
            print(f"  ⚠️ 在 sora_videos 表中未找到草稿记录 (ID: {draft_id} 或 {generation_id})")
        
        # 步骤 2: 通过 sora_task_id 查找并更新 tasks 表
        if task_id:
            cursor.execute("""
                SELECT id, prompt, status
                FROM tasks
                WHERE sora_task_id = %s
            """, (task_id,))
            
            task = cursor.fetchone()
            
            if task:
                local_task_id = task['id']
                prompt = task['prompt']
                status = task['status']
                print(f"  ✅ 通过 sora_task_id 找到任务: {local_task_id}")
                print(f"     提示词: {prompt[:50] if prompt else 'N/A'}...")
                print(f"     状态: {status}")
                
                # 更新任务信息
                cursor.execute("""
                    UPDATE tasks
                    SET post_id = %s,
                        permalink = %s,
                        posted_at = %s,
                        is_published = 1,
                        status = 'published',
                        draft_id = %s,
                        generation_id = %s
                    WHERE id = %s
                """, (post_id, published_url, timestamp, 
                      draft_id, generation_id, local_task_id))
                
                # 🆕 获取任务的 profile_id 以释放窗口
                cursor.execute("SELECT profile_id FROM tasks WHERE id = %s", (local_task_id,))
                profile_row = cursor.fetchone()
                
                conn.commit()
                conn.close()
                
                print(f"  ✅ 任务 {local_task_id} 已更新")
                print(f"  ✅ 绑定关系: draft_id={draft_id} → post_id={post_id}")
                
                # 🆕 释放窗口：任务真正完成了
                if profile_row and profile_row.get('profile_id'):
                    profile_id = profile_row['profile_id']
                    with window_manager.lock:
                        if profile_id in window_manager.window_status:
                            window_manager.window_status[profile_id] = {
                                'status': 'idle',
                                'current_task_id': None
                            }
                    print(f"  ✅ 窗口 {profile_id} 已释放（任务已发布）")
                
                print(f"{'='*80}\n")
                
                return {
                    "success": True,
                    "message": "发布结果已保存并同步到 sora_videos 表",
                    "task_id": local_task_id,
                    "binding": {
                        "draft_id": draft_id,
                        "post_id": post_id
                    }
                }
        
        # 步骤 3: 如果没有找到任务，记录到单独的绑定表
        print(f"  ⚠️ 未找到对应的任务 (sora_task_id={task_id})")
        print(f"  💡 建议: 在数据库中创建 draft_post_binding 表来记录绑定关系")
        
        # 尝试创建绑定表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS draft_post_binding (
                id INT AUTO_INCREMENT PRIMARY KEY,
                draft_id VARCHAR(255) NOT NULL,
                generation_id VARCHAR(255),
                task_id VARCHAR(255),
                draft_url TEXT,
                post_id VARCHAR(255) NOT NULL,
                published_url TEXT NOT NULL,
                created_at VARCHAR(255) NOT NULL,
                UNIQUE KEY unique_draft (draft_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 插入或更新绑定关系
        cursor.execute("""
            INSERT INTO draft_post_binding
            (draft_id, generation_id, task_id, draft_url, post_id, published_url, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                generation_id = VALUES(generation_id),
                task_id = VALUES(task_id),
                draft_url = VALUES(draft_url),
                post_id = VALUES(post_id),
                published_url = VALUES(published_url),
                created_at = VALUES(created_at)
        """, (draft_id, generation_id, task_id, draft_url, post_id, published_url, timestamp))
        
        conn.commit()
        conn.close()
        
        print(f"  ✅ 绑定关系已保存到 draft_post_binding 表")
        print(f"  ✅ 绑定: draft_id={draft_id} → post_id={post_id}")
        print(f"{'='*80}\n")
        
        return {
            "success": True,
            "message": "发布结果已保存到绑定表并同步到 sora_videos 表",
            "binding": {
                "draft_id": draft_id,
                "post_id": post_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Plug-in 发布结果] 失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



# ==================== 草稿队列管理 ====================

# 内存中的草稿队列
draft_queue = []
draft_queue_lock = None

@app.post("/api/drafts/queue")
async def add_to_draft_queue(data: dict):
    """
    接收 plug-renwu 发送的未发布草稿队列
    
    数据格式:
    {
        "drafts": [
            {
                "draft_id": "gen_xxx",
                "generation_id": "gen_xxx",
                "task_id": "task_xxx",
                "prompt": "提示词",
                "draft_url": "https://sora.chatgpt.com/d/gen_xxx",
                "thumbnail_url": "..."
            }
        ],
        "timestamp": "2026-02-04T10:30:00.000Z"
    }
    """
    global draft_queue
    
    try:
        drafts = data.get('drafts', [])
        timestamp = data.get('timestamp')
        
        print(f"\n{'='*80}")
        print(f"[草稿队列] 收到 {len(drafts)} 个未发布草稿")
        print(f"{'='*80}")
        print(f"  时间: {timestamp}")
        
        # 清空旧队列，使用新队列
        draft_queue = []
        
        for draft in drafts:
            draft_id = draft.get('draft_id')
            task_id = draft.get('task_id')
            prompt = draft.get('prompt', '')
            
            # 检查是否已在队列中
            if not any(d.get('draft_id') == draft_id for d in draft_queue):
                draft_queue.append(draft)
                print(f"  ➕ {draft_id} - {prompt[:50]}...")
        
        print(f"\n  📋 当前队列长度: {len(draft_queue)}")
        print(f"{'='*80}\n")
        
        return {
            "success": True,
            "message": f"已添加 {len(draft_queue)} 个草稿到队列",
            "queue_length": len(draft_queue)
        }
        
    except Exception as e:
        print(f"[草稿队列] 添加失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drafts/queue")
async def get_draft_queue():
    """
    获取当前的草稿队列
    plug-in 通过此接口获取待发布的草稿
    """
    try:
        print(f"\n[草稿队列] plug-in 请求队列，当前长度: {len(draft_queue)}")
        
        return {
            "success": True,
            "drafts": draft_queue,
            "queue_length": len(draft_queue),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[草稿队列] 获取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/drafts/queue/{draft_id}")
async def remove_from_draft_queue(draft_id: str):
    """
    从队列中移除已处理的草稿
    """
    global draft_queue
    
    try:
        original_length = len(draft_queue)
        draft_queue = [d for d in draft_queue if d.get('draft_id') != draft_id]
        removed = original_length - len(draft_queue)
        
        if removed > 0:
            print(f"[草稿队列] 已移除: {draft_id}, 剩余: {len(draft_queue)}")
            return {
                "success": True,
                "message": f"已移除草稿 {draft_id}",
                "queue_length": len(draft_queue)
            }
        else:
            return {
                "success": False,
                "message": f"草稿 {draft_id} 不在队列中",
                "queue_length": len(draft_queue)
            }
        
    except Exception as e:
        print(f"[草稿队列] 移除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drafts/queue/clear")
async def clear_draft_queue():
    """
    清空草稿队列
    """
    global draft_queue
    
    try:
        count = len(draft_queue)
        draft_queue = []
        
        print(f"[草稿队列] 已清空，移除了 {count} 个草稿")
        
        return {
            "success": True,
            "message": f"已清空队列，移除了 {count} 个草稿",
            "queue_length": 0
        }
        
    except Exception as e:
        print(f"[草稿队列] 清空失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

