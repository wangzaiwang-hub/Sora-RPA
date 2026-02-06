#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
强制关闭 ixBrowser 窗口
用于清理卡住的窗口状态
"""

import sys
from ixBrowser import ixBrowser

def force_close_window(profile_id):
    """强制关闭指定窗口"""
    print("=" * 60)
    print(f"强制关闭窗口 {profile_id}")
    print("=" * 60)
    
    client = ixBrowser()
    
    # 尝试多次关闭
    max_attempts = 5
    for attempt in range(max_attempts):
        print(f"\n尝试 {attempt + 1}/{max_attempts}...")
        
        try:
            result = client.close_profile(profile_id)
            
            if result:
                print(f"✓ 窗口 {profile_id} 已关闭")
                return True
            else:
                error_msg = str(client.message)
                print(f"⚠️  关闭失败: {error_msg}")
                
                # 如果是进程不存在，说明窗口已经关闭了
                if 'Process not found' in error_msg or '进程不存在' in error_msg:
                    print(f"ℹ️  窗口进程不存在，可能已经关闭")
                    
                    # 尝试打开再关闭，清理状态
                    print(f"尝试打开窗口以清理状态...")
                    try:
                        open_result = client.open_profile(
                            profile_id,
                            cookies_backup=False,
                            load_profile_info_page=False
                        )
                        
                        if open_result:
                            print(f"✓ 窗口已打开，现在关闭...")
                            import time
                            time.sleep(2)
                            close_result = client.close_profile(profile_id)
                            if close_result:
                                print(f"✓ 窗口 {profile_id} 已关闭")
                                return True
                        else:
                            print(f"⚠️  打开失败: {client.message}")
                    except Exception as e:
                        print(f"⚠️  打开窗口失败: {e}")
                
                if attempt < max_attempts - 1:
                    import time
                    print(f"等待 2 秒后重试...")
                    time.sleep(2)
                    
        except Exception as e:
            print(f"❌ 关闭窗口时出错: {e}")
            if attempt < max_attempts - 1:
                import time
                print(f"等待 2 秒后重试...")
                time.sleep(2)
    
    print(f"\n❌ 无法关闭窗口 {profile_id}")
    print(f"💡 建议：请在 ixBrowser 客户端中手动关闭窗口")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python force_close_window.py <窗口ID>")
        print("示例: python force_close_window.py 34")
        sys.exit(1)
    
    try:
        profile_id = int(sys.argv[1])
        force_close_window(profile_id)
    except ValueError:
        print("错误: 窗口ID必须是数字")
        sys.exit(1)
