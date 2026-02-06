#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
窗口管理模块
"""

import sys
import os
from datetime import datetime
from typing import List, Dict
import threading
import time
import atexit

# 添加 python自动化 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python自动化'))

from sora_automation import SoraAutomation
from ixbrowser_local_api import IXBrowserClient
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from config import AUTO_CLOSE_WINDOWS_ON_SHUTDOWN, AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP

class WindowManager:
    def __init__(self, database):
        self.db = database
        self.client = IXBrowserClient()
        self.active_windows = {}  # profile_id -> SoraAutomation
        self.window_status = {}  # profile_id -> {'status': 'idle'/'busy', 'current_task_id': None}
        self.lock = threading.Lock()
        self.task_queue_running = False
        
        # 🆕 启动时自动修复误判为失败的任务
        self._auto_fix_failed_tasks()
        
        # 注册退出时的清理函数
        atexit.register(self._cleanup_on_shutdown)
        
        # 启动时检测已打开的窗口（如果配置启用）
        if AUTO_DETECT_OPEN_WINDOWS_ON_STARTUP:
            self._detect_open_windows()
    
    def _auto_fix_failed_tasks(self):
        """自动修复状态为 failed 但有 video_url 的任务"""
        try:
            # 直接在这里实现修复逻辑
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 查找状态为 failed 但有 video_url 的任务
            cursor.execute("""
                SELECT id, video_url FROM tasks 
                WHERE status = 'failed' AND video_url IS NOT NULL AND video_url != ''
            """)
            
            tasks = cursor.fetchall()
            count = 0
            
            for task in tasks:
                task_id = task['id']
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'success', progress = 100, progress_message = 'completed'
                    WHERE id = %s
                """, (task_id,))
                count += 1
            
            conn.commit()
            conn.close()
            
            if count > 0:
                print(f"✅ 启动时自动修复了 {count} 个误判为失败的任务")
        except Exception as e:
            print(f"⚠️ 自动修复失败任务时出错: {e}")
            # 不影响主程序启动
    
    def _start_task_queue_monitor(self):
        """启动任务队列监控"""
        if not self.task_queue_running:
            self.task_queue_running = True
            threading.Thread(target=self._task_queue_worker, daemon=True).start()
            print("任务队列监控已启动")
    
    def _task_queue_worker(self):
        """任务队列工作线程 - 自动分配任务给空闲窗口"""
        while self.task_queue_running:
            try:
                # 检查是否有空闲窗口
                idle_windows = []
                with self.lock:
                    for profile_id, status in self.window_status.items():
                        # 只选择状态为 'idle' 的窗口，排除 'busy' 和 'stopped'
                        if status['status'] == 'idle' and profile_id in self.active_windows:
                            idle_windows.append(profile_id)
                
                if idle_windows:
                    # 快速读取待处理任务到内存（减少数据库锁定时间）
                    pending_tasks = self.db.get_pending_tasks(limit=len(idle_windows))
                    
                    if pending_tasks:
                        print(f"发现 {len(idle_windows)} 个空闲窗口和 {len(pending_tasks)} 个待处理任务")
                        
                        # 批量分配任务
                        assignments = []  # [(profile_id, task_id, task_data), ...]
                        
                        for i, task in enumerate(pending_tasks):
                            if i < len(idle_windows):
                                profile_id = idle_windows[i]
                                # 将任务数据缓存到内存，并更新 profile_id
                                task_data = dict(task)
                                task_data['profile_id'] = profile_id  # 在缓存中设置窗口ID
                                assignments.append((profile_id, task['id'], task_data))
                        
                        # 批量更新数据库（一次性完成，减少锁定时间）
                        if assignments:
                            conn = self.db.get_connection()
                            cursor = conn.cursor()
                            try:
                                for profile_id, task_id, _ in assignments:
                                    cursor.execute(
                                        "UPDATE tasks SET profile_id = %s WHERE id = %s",
                                        (profile_id, task_id)
                                    )
                                conn.commit()
                            except Exception as e:
                                print(f"批量更新任务失败: {e}")
                                conn.rollback()
                            finally:
                                conn.close()
                        
                        # 更新窗口状态并启动任务执行（使用缓存的任务数据）
                        for profile_id, task_id, task_data in assignments:
                            # 标记窗口为忙碌
                            with self.lock:
                                self.window_status[profile_id] = {
                                    'status': 'busy',
                                    'current_task_id': task_id
                                }
                            
                            # 启动任务执行（传入缓存的任务数据）
                            threading.Thread(
                                target=self._execute_task_and_continue,
                                args=(profile_id, task_id, task_data),
                                daemon=True
                            ).start()
                            
                            print(f"  分配任务 {task_id} 到窗口 {profile_id}")
                
                # 缩短检查间隔到2秒
                time.sleep(2)
                
            except Exception as e:
                print(f"任务队列工作线程出错: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(2)
    
    def _execute_task_and_continue(self, profile_id: int, task_id: int, task_data: Dict = None):
        """执行任务并在完成后继续处理队列"""
        task_success = False
        try:
            result = self.execute_task(task_id, task_data)
            # 检查任务是否成功
            task = self.db.get_task_by_id(task_id)
            if task and task['status'] == 'success':
                task_success = True
        except Exception as e:
            print(f"任务执行异常: {e}")
            task_success = False
        finally:
            if task_success:
                # 任务成功，随机等待60-120秒后继续领取新任务
                import random
                wait_time = random.randint(60, 120)
                print(f"窗口 {profile_id} 任务成功完成，等待 {wait_time} 秒后再领取新任务...")
                time.sleep(wait_time)
                
                # 标记窗口为空闲
                with self.lock:
                    if profile_id in self.window_status:
                        self.window_status[profile_id] = {
                            'status': 'idle',
                            'current_task_id': None
                        }
                print(f"窗口 {profile_id} 已标记为空闲，可以领取新任务")
            else:
                # 任务失败，只标记窗口为空闲，不关闭窗口
                # 这样窗口可以继续处理其他任务
                print(f"窗口 {profile_id} 任务失败，标记为空闲状态（保持窗口打开）")
                with self.lock:
                    if profile_id in self.window_status:
                        self.window_status[profile_id] = {
                            'status': 'idle',  # 标记为空闲，而不是error
                            'current_task_id': None
                        }
                print(f"窗口 {profile_id} 已标记为空闲，可以继续领取新任务")
    
    def _cleanup_on_shutdown(self):
        """后端关闭时的清理操作"""
        if AUTO_CLOSE_WINDOWS_ON_SHUTDOWN:
            print("\n后端正在关闭，自动关闭所有窗口...")
            profile_ids = list(self.active_windows.keys())
            if profile_ids:
                results = self.close_windows(profile_ids)
                success_count = sum(1 for r in results if r['status'] == 'success')
                print(f"已关闭 {success_count}/{len(profile_ids)} 个窗口")
            else:
                print("没有需要关闭的窗口")
        else:
            print("\n后端正在关闭，保持窗口打开状态...")
    
    def _detect_open_windows(self):
        """检测并连接到已打开的窗口"""
        print("检测已打开的窗口...")
        
        try:
            # 获取所有账号
            accounts = self.db.get_all_accounts()
            
            for account in accounts:
                profile_id = account.get('profile_id')
                if not profile_id:
                    continue
                
                try:
                    # 尝试打开窗口，如果已打开会返回错误
                    result = self.client.open_profile(
                        profile_id,
                        cookies_backup=False,
                        load_profile_info_page=False
                    )
                    
                    # 检查是否已打开
                    if result is None and self.client.message:
                        error_msg = str(self.client.message).lower()
                        if 'already open' in error_msg or '已经打开' in error_msg or '已打开' in error_msg:
                            print(f"  检测到窗口 {profile_id} 已打开，尝试连接...")
                            
                            # 再次调用获取连接信息
                            time.sleep(0.5)
                            result = self.client.open_profile(
                                profile_id,
                                cookies_backup=False,
                                load_profile_info_page=False
                            )
                            
                            if result and 'debugging_address' in result:
                                try:
                                    automation = SoraAutomation(profile_id=profile_id)
                                    automation.debugging_address = result['debugging_address']
                                    
                                    # 连接到已打开的浏览器
                                    chrome_options = Options()
                                    chrome_options.add_experimental_option("debuggerAddress", result['debugging_address'])
                                    
                                    automation.driver = Chrome(
                                        service=Service(result['webdriver']),
                                        options=chrome_options
                                    )
                                    
                                    with self.lock:
                                        self.active_windows[profile_id] = automation
                                    
                                    print(f"  ✓ 已连接到窗口 {profile_id}")
                                except Exception as e:
                                    print(f"  ✗ 连接窗口 {profile_id} 失败: {e}")
                    elif result:
                        # 窗口被打开了（之前是关闭的），立即关闭
                        try:
                            self.client.close_profile(profile_id)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"  检测窗口 {profile_id} 时出错: {e}")
                    
        except Exception as e:
            print(f"检测已打开窗口失败: {e}")
        
        print(f"检测完成，已连接 {len(self.active_windows)} 个窗口")
    
    def open_windows(self, profile_ids: List[int]) -> Dict:
        """批量打开窗口"""
        results = []
        
        for profile_id in profile_ids:
            try:
                # 检查窗口是否已打开
                if profile_id in self.active_windows:
                    results.append({
                        "profile_id": profile_id,
                        "status": "already_open",
                        "message": "窗口已打开"
                    })
                    continue
                
                # 打开窗口
                automation = SoraAutomation(profile_id=profile_id)
                automation._open_browser()
                
                with self.lock:
                    self.active_windows[profile_id] = automation
                
                # 检测登录状态
                print(f"检测窗口 {profile_id} 的登录状态...")
                is_logged_in = automation._check_login_status()
                
                # 查找该窗口对应的账号
                accounts = self.db.get_all_accounts()
                account = next((acc for acc in accounts if acc.get('profile_id') == profile_id), None)
                
                print(f"窗口 {profile_id} 查找账号结果: {account}")
                print(f"窗口 {profile_id} 登录状态: {'已登录' if is_logged_in else '未登录'}")
                
                if account:
                    # 如果未登录，尝试登录
                    if not is_logged_in:
                        print(f"窗口 {profile_id} 未登录，尝试登录账号 {account['username']}")
                        login_success = automation._login_account(account['username'], account['password'])
                        
                        if not login_success:
                            results.append({
                                "profile_id": profile_id,
                                "status": "warning",
                                "message": "窗口已打开，但登录失败，请手动登录"
                            })
                            continue
                    else:
                        print(f"窗口 {profile_id} 已登录，跳过登录步骤")
                else:
                    print(f"窗口 {profile_id} 未关联账号，但已登录，将直接导航到 Sora")
                
                # 无论是否有关联账号，只要已登录就导航到 Sora 页面
                if is_logged_in:
                    automation._navigate_to_sora()
                else:
                    print(f"窗口 {profile_id} 未登录且无关联账号，请手动登录")
                
                # 标记窗口为空闲状态
                with self.lock:
                    self.window_status[profile_id] = {
                        'status': 'idle',
                        'current_task_id': None
                    }
                
                # 启动任务队列监控（如果还没启动）
                self._start_task_queue_monitor()
                
                results.append({
                    "profile_id": profile_id,
                    "status": "success",
                    "message": f"窗口已打开{'（已登录）' if is_logged_in else '（已登录）'}，等待任务分配"
                })
                
            except Exception as e:
                results.append({
                    "profile_id": profile_id,
                    "status": "error",
                    "message": str(e)
                })
        
        return results
    
    def close_windows(self, profile_ids: List[int]) -> Dict:
        """批量关闭窗口 - 带超时和强制关闭"""
        results = []
        
        for profile_id in profile_ids:
            print(f"\n开始关闭窗口 {profile_id}...")
            try:
                # 检查窗口是否在活跃列表中
                if profile_id not in self.active_windows:
                    print(f"  窗口 {profile_id} 不在活跃列表中，尝试通过 API 关闭...")
                    try:
                        result = self.client.close_profile(profile_id)
                        if result:
                            print(f"  ✓ 窗口 {profile_id} 已通过API关闭")
                        else:
                            print(f"  ⚠️  API返回: {self.client.message}")
                    except Exception as e:
                        print(f"  ⚠️  API关闭失败: {e}")
                    
                    results.append({
                        "profile_id": profile_id,
                        "status": "success",
                        "message": "窗口已关闭"
                    })
                    continue
                
                # 窗口在活跃列表中，需要清理
                print(f"  窗口 {profile_id} 在活跃列表中，开始清理...")
                automation = self.active_windows[profile_id]
                
                # 使用线程来执行cleanup，避免主线程卡住
                import threading
                cleanup_done = [False]
                cleanup_error = [None]
                
                def do_cleanup():
                    try:
                        automation.cleanup()
                        cleanup_done[0] = True
                    except Exception as e:
                        cleanup_error[0] = e
                
                cleanup_thread = threading.Thread(target=do_cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()
                cleanup_thread.join(timeout=10)  # 最多等待10秒
                
                if not cleanup_done[0]:
                    print(f"  ⚠️  窗口 {profile_id} cleanup超时，强制清理...")
                
                if cleanup_error[0]:
                    print(f"  ⚠️  cleanup出错: {cleanup_error[0]}")
                
                # 无论cleanup是否成功，都从活跃列表中移除
                with self.lock:
                    if profile_id in self.active_windows:
                        del self.active_windows[profile_id]
                        print(f"  ✓ 已从活跃列表移除窗口 {profile_id}")
                    
                    if profile_id in self.window_status:
                        del self.window_status[profile_id]
                        print(f"  ✓ 已清除窗口 {profile_id} 的状态")
                
                # 释放该窗口的待处理任务
                try:
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE tasks 
                        SET profile_id = NULL 
                        WHERE profile_id = %s AND status IN ('pending', 'running')
                    """, (profile_id,))
                    released_count = cursor.rowcount
                    conn.commit()
                    conn.close()
                    if released_count > 0:
                        print(f"  ✓ 释放了窗口 {profile_id} 的 {released_count} 个任务")
                except Exception as e:
                    print(f"  ⚠️  释放任务失败: {e}")
                
                # 最后尝试通过API强制关闭（确保窗口真的关闭）
                try:
                    print(f"  最后通过API确保窗口 {profile_id} 关闭...")
                    self.client.close_profile(profile_id)
                except:
                    pass
                
                results.append({
                    "profile_id": profile_id,
                    "status": "success",
                    "message": "窗口已关闭"
                })
                
                print(f"✓ 窗口 {profile_id} 关闭完成\n")
                
            except Exception as e:
                print(f"✗ 关闭窗口 {profile_id} 失败: {e}\n")
                import traceback
                traceback.print_exc()
                
                # 即使出错，也尝试从列表中移除
                try:
                    with self.lock:
                        if profile_id in self.active_windows:
                            del self.active_windows[profile_id]
                        if profile_id in self.window_status:
                            del self.window_status[profile_id]
                except:
                    pass
                
                results.append({
                    "profile_id": profile_id,
                    "status": "error",
                    "message": str(e)
                })
        
        # 检查是否所有窗口都已关闭
        if len(self.active_windows) == 0:
            print("所有窗口已关闭，释放所有队列中的任务...")
            try:
                conn = self.db.get_connection()
                cursor = conn.cursor()
                # 将 running 状态的任务重置为 pending
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'pending', profile_id = NULL, start_time = NULL
                    WHERE status = 'running'
                """)
                running_count = cursor.rowcount
                # 清除 pending 任务的 profile_id
                cursor.execute("""
                    UPDATE tasks 
                    SET profile_id = NULL 
                    WHERE status = 'pending'
                """)
                pending_count = cursor.rowcount
                conn.commit()
                conn.close()
                if running_count > 0:
                    print(f"重置了 {running_count} 个进行中的任务为待处理状态")
                if pending_count > 0:
                    print(f"释放了 {pending_count} 个待处理任务")
            except Exception as e:
                print(f"释放队列任务失败: {e}")
        
        return results
    
    def get_window_status(self, profile_id: int) -> Dict:
        """获取窗口状态"""
        # 检查是否在活跃窗口列表中
        is_open = profile_id in self.active_windows
        
        return {
            "profile_id": profile_id,
            "is_open": is_open,
            "status": "active" if is_open else "inactive"
        }
    
    def get_all_windows_status(self) -> List[Dict]:
        """获取所有窗口状态"""
        statuses = []
        
        try:
            # 从 ixBrowser API 获取所有窗口
            all_profiles = self.client.get_profile_list(limit=100)
            
            if all_profiles:
                # 获取所有账号信息，用于匹配
                accounts = self.db.get_all_accounts()
                account_map = {acc['profile_id']: acc for acc in accounts if acc.get('profile_id')}
                
                for profile in all_profiles:
                    profile_id = profile.get('profile_id')
                    if profile_id:
                        status = self.get_window_status(profile_id)
                        status['name'] = profile.get('name', f'窗口 {profile_id}')
                        
                        # 添加窗口工作状态
                        if profile_id in self.window_status:
                            window_state = self.window_status[profile_id]
                            status['work_status'] = window_state['status']
                            status['current_task_id'] = window_state.get('current_task_id')
                            # 如果是异常状态，添加错误时间
                            if window_state['status'] == 'error':
                                status['error_time'] = window_state.get('error_time')
                        else:
                            status['work_status'] = 'unknown'
                            status['current_task_id'] = None
                        
                        # 如果窗口已关联账号，添加账号信息
                        if profile_id in account_map:
                            account = account_map[profile_id]
                            status['username'] = account['username']
                            status['account_id'] = account['id']
                            status['has_account'] = True
                        else:
                            status['username'] = '未关联'
                            status['account_id'] = None
                            status['has_account'] = False
                        
                        statuses.append(status)
        except Exception as e:
            print(f"获取窗口列表失败: {e}")
        
        return statuses
    
    def _auto_execute_tasks(self, account_id: int, profile_id: int, tasks: List[Dict]):
        """自动执行账号的所有待处理任务（已废弃，使用任务队列代替）"""
        print(f"开始自动执行账号 {account_id} 的 {len(tasks)} 个任务")
        
        for task in tasks:
            try:
                self.execute_task(task['id'])
            except Exception as e:
                print(f"执行任务 {task['id']} 失败: {e}")
        
        # 所有任务完成后，更新账号状态
        self.db.update_account_status(account_id, 'inactive')
        print(f"账号 {account_id} 的所有任务已完成")
    
    def execute_task(self, task_id: int, task_data: Dict = None):
        """执行任务"""
        print(f"\n========== 开始执行任务 {task_id} ==========")
        
        # 如果有缓存的任务数据，直接使用；否则从数据库读取
        if task_data:
            task = task_data
            print(f"使用缓存的任务数据")
        else:
            task = self.db.get_task_by_id(task_id)
            if not task:
                print(f"任务 {task_id} 不存在")
                return
        
        print(f"任务信息: ID={task_id}, 提示词={task['prompt'][:50]}...")
        
        profile_id = task.get('profile_id')
        if not profile_id:
            print(f"任务 {task_id} 未分配窗口")
            self.db.update_task_status(
                task_id, 
                'failed', 
                error_message='任务未分配窗口'
            )
            self.db.update_task_progress(task_id, 0, '任务未分配窗口')
            return
        
        print(f"任务分配到窗口: {profile_id}")
        
        try:
            # 进度 0%: 初始化
            self.db.update_task_progress(task_id, 0, '任务初始化')
            
            # 更新任务状态为运行中
            print(f"更新任务 {task_id} 状态为 running")
            self.db.update_task_status(
                task_id, 
                'running',
                start_time=datetime.now().isoformat()
            )
            
            # 进度 10%: 准备窗口
            self.db.update_task_progress(task_id, 10, '准备浏览器窗口')
            
            # 获取或创建自动化实例
            if profile_id not in self.active_windows:
                print(f"窗口 {profile_id} 未打开")
                self.db.update_task_status(
                    task_id,
                    'failed',
                    end_time=datetime.now().isoformat(),
                    error_message='窗口未打开'
                )
                self.db.update_task_progress(task_id, 0, '窗口未打开')
                return
            
            automation = self.active_windows[profile_id]
            print(f"获取到窗口 {profile_id} 的自动化实例")
            
            # 进度 20%: 导航到Sora页面
            self.db.update_task_progress(task_id, 20, '导航到Sora页面')
            
            # 执行视频生成（带进度回调）
            print(f"开始生成视频...")
            
            # 进度 30%: 输入提示词
            self.db.update_task_progress(task_id, 30, '输入提示词')
            
            result = automation.generate_video(
                prompt=task['prompt'],
                image=task.get('image'),
                auto_download=True,
                progress_callback=lambda progress, message: self.db.update_task_progress(task_id, progress, message),
                task_id=task_id  # 传入task_id用于检查进度
            )
            
            print(f"视频生成结果: {result}")
            
            # 更新任务状态
            if result['success']:
                print(f"任务 {task_id} 执行成功")
                self.db.update_task_status(
                    task_id,
                    'success',
                    end_time=datetime.now().isoformat(),
                    video_url=result.get('video_url')
                )
                # 进度 100%: 完成
                self.db.update_task_progress(task_id, 100, '视频生成完成')
                # 注意：窗口不在这里释放，等待发布完成后再释放
            else:
                print(f"任务 {task_id} 执行失败: {result.get('error')}")
                self.db.update_task_status(
                    task_id,
                    'failed',
                    end_time=datetime.now().isoformat(),
                    error_message=result.get('error')
                )
                self.db.update_task_progress(task_id, 0, f'失败: {result.get("error")}')
                
                # 🆕 任务失败时释放窗口
                with self.lock:
                    if profile_id in self.window_status:
                        self.window_status[profile_id] = {
                            'status': 'idle',
                            'current_task_id': None
                        }
                print(f"  ✅ 窗口 {profile_id} 已释放（任务失败）")
            
        except Exception as e:
            print(f"任务 {task_id} 执行异常: {e}")
            import traceback
            traceback.print_exc()
            self.db.update_task_status(
                task_id,
                'failed',
                end_time=datetime.now().isoformat(),
                error_message=str(e)
            )
            self.db.update_task_progress(task_id, 0, f'异常: {str(e)}')
            
            # 🆕 任务异常时释放窗口
            with self.lock:
                if profile_id in self.window_status:
                    self.window_status[profile_id] = {
                        'status': 'idle',
                        'current_task_id': None
                    }
            print(f"  ✅ 窗口 {profile_id} 已释放（任务异常）")
        
        print(f"========== 任务 {task_id} 执行完成 ==========\n")
