#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清理重复任务 - MySQL 版本
"""

from database import Database

def cleanup_duplicates():
    """清理重复任务"""
    print("=" * 80)
    print("清理重复任务 (MySQL)")
    print("=" * 80)
    
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 1. 查看当前任务数量
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_before = cursor.fetchone()['count']
    print(f"\n📊 当前任务总数: {total_before}")
    
    # 2. 查找重复任务（相同提示词和图片）
    print("\n🔍 查找重复任务...")
    cursor.execute("""
        SELECT 
            TRIM(prompt) as clean_prompt,
            COALESCE(image, '') as clean_image,
            COUNT(*) as count,
            GROUP_CONCAT(id ORDER BY id) as ids
        FROM tasks
        GROUP BY clean_prompt, clean_image
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"\n⚠️  发现 {len(duplicates)} 组重复任务:")
        
        total_to_delete = 0
        for dup in duplicates:
            clean_prompt = dup['clean_prompt']
            clean_image = dup['clean_image']
            count = dup['count']
            ids = dup['ids']
            ids_list = [int(x) for x in ids.split(',')]
            to_delete = count - 1
            total_to_delete += to_delete
            
            print(f"\n  提示词: {clean_prompt[:50]}...")
            print(f"  图片: {'有' if clean_image else '无'}")
            print(f"  重复次数: {count}")
            print(f"  任务 ID: {ids}")
            print(f"  将保留: ID {ids_list[0]}")
            print(f"  将删除: {to_delete} 个任务")
        
        # 3. 询问是否删除
        print(f"\n📊 总计将删除 {total_to_delete} 个重复任务")
        confirm = input("\n是否继续删除重复任务? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ 操作已取消")
            conn.close()
            return
        
        # 4. 删除重复任务（保留每组中 ID 最小的）
        print("\n🗑️  删除重复任务...")
        deleted_count = 0
        
        for dup in duplicates:
            ids = dup['ids']
            ids_list = [int(x) for x in ids.split(',')]
            keep_id = ids_list[0]  # 保留第一个（ID 最小的）
            delete_ids = ids_list[1:]  # 删除其他的
            
            for delete_id in delete_ids:
                cursor.execute("DELETE FROM tasks WHERE id = %s", (delete_id,))
                deleted_count += 1
                print(f"  ✅ 删除任务 ID: {delete_id}")
        
        conn.commit()
        print(f"\n✅ 已删除 {deleted_count} 个重复任务")
    else:
        print("\n✅ 没有发现重复任务")
    
    # 5. 查看删除后的任务数量
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_after = cursor.fetchone()['count']
    print(f"\n📊 删除后任务总数: {total_after}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 清理完成")
    print("=" * 80)
    print(f"\n总结:")
    print(f"  删除前: {total_before} 个任务")
    print(f"  删除后: {total_after} 个任务")
    print(f"  删除了: {total_before - total_after} 个重复任务")
    print(f"\n注意: MySQL 使用 AUTO_INCREMENT，不需要手动重新排序 ID")

if __name__ == "__main__":
    try:
        cleanup_duplicates()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
