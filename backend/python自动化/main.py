#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sora 视频批量生成工具 - Python 版本
使用 ixBrowser 官方 API + Selenium
"""

import sys
import time
import json
import csv
from pathlib import Path
from sora_automation import SoraAutomation

def load_tasks_from_json(file_path):
    """从 JSON 文件加载任务"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def load_tasks_from_csv(file_path):
    """从 CSV 文件加载任务"""
    tasks = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append({
                'prompt': row.get('prompt', ''),
                'image': row.get('image', None)
            })
    return tasks

def main():
    print('=' * 60)
    print('Sora 视频批量生成工具 - Python 版本')
    print('=' * 60)
    print()
    
    # 1. 加载任务文件
    if len(sys.argv) < 2:
        print('使用方法: python main.py <任务文件>')
        print('示例: python main.py tasks.json')
        print('      python main.py tasks.csv')
        sys.exit(1)
    
    task_file = sys.argv[1]
    file_path = Path(task_file)
    
    if not file_path.exists():
        print(f'错误: 文件不存在 - {task_file}')
        sys.exit(1)
    
    # 根据文件类型加载任务
    if file_path.suffix == '.json':
        tasks = load_tasks_from_json(task_file)
    elif file_path.suffix == '.csv':
        tasks = load_tasks_from_csv(task_file)
    else:
        print(f'错误: 不支持的文件格式 - {file_path.suffix}')
        print('支持的格式: .json, .csv')
        sys.exit(1)
    
    print(f'✓ 已加载 {len(tasks)} 个任务')
    print()
    
    # 2. 配置参数
    interval = 10  # 任务间隔（秒）
    auto_download = True  # 自动下载
    
    if len(sys.argv) >= 3:
        interval = int(sys.argv[2])
    
    print(f'配置:')
    print(f'  - 任务数量: {len(tasks)}')
    print(f'  - 任务间隔: {interval} 秒')
    print(f'  - 自动下载: {"是" if auto_download else "否"}')
    print()
    
    # 3. 初始化自动化工具
    automation = SoraAutomation()
    
    # 4. 执行批量生成
    print('开始批量生成...')
    print()
    
    results = []
    for i, task in enumerate(tasks, 1):
        print(f'[{i}/{len(tasks)}] 处理任务: {task["prompt"][:50]}...')
        
        try:
            result = automation.generate_video(
                prompt=task['prompt'],
                image=task.get('image'),
                auto_download=auto_download
            )
            
            if result['success']:
                print(f'  ✓ 成功 (耗时: {result["duration"]:.1f}秒)')
                results.append({'task': i, 'status': 'success', 'result': result})
            else:
                print(f'  ✗ 失败: {result.get("error", "未知错误")}')
                results.append({'task': i, 'status': 'failed', 'error': result.get('error')})
        
        except Exception as e:
            print(f'  ✗ 异常: {str(e)}')
            results.append({'task': i, 'status': 'error', 'error': str(e)})
        
        # 任务间隔
        if i < len(tasks):
            print(f'  等待 {interval} 秒...')
            time.sleep(interval)
        
        print()
    
    # 5. 统计结果
    print('=' * 60)
    print('批量生成完成')
    print('=' * 60)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count
    
    print(f'总任务数: {len(tasks)}')
    print(f'成功: {success_count}')
    print(f'失败: {failed_count}')
    print()
    
    # 保存结果
    result_file = f'results_{int(time.time())}.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f'结果已保存到: {result_file}')
    
    # 清理
    automation.cleanup()

if __name__ == '__main__':
    main()
