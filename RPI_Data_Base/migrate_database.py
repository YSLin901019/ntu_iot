#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫遷移腳本
為現有數據庫添加新欄位
"""

import sqlite3
import os

DB_FILE = "shelf_data.db"

def check_column_exists(cursor, table_name, column_name):
    """檢查欄位是否存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """執行數據庫遷移"""
    
    if not os.path.exists(DB_FILE):
        print(f"❌ 找不到數據庫文件: {DB_FILE}")
        print("請先運行系統創建數據庫")
        return False
    
    print("=" * 60)
    print("數據庫遷移腳本")
    print("=" * 60)
    print(f"數據庫文件: {DB_FILE}\n")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    migrations_done = []
    
    # 遷移 1: 為 shelves 表添加 gpio 欄位
    if not check_column_exists(cursor, 'shelves', 'gpio'):
        print("📝 添加 shelves.gpio 欄位...")
        try:
            cursor.execute('ALTER TABLE shelves ADD COLUMN gpio INTEGER')
            migrations_done.append("✅ 添加 shelves.gpio")
        except Exception as e:
            print(f"❌ 失敗: {e}")
    else:
        print("✓ shelves.gpio 欄位已存在")
    
    # 遷移 2: 為 shelves 表添加 enabled 欄位
    if not check_column_exists(cursor, 'shelves', 'enabled'):
        print("📝 添加 shelves.enabled 欄位...")
        try:
            cursor.execute('ALTER TABLE shelves ADD COLUMN enabled INTEGER DEFAULT 0')
            migrations_done.append("✅ 添加 shelves.enabled (預設值: 0)")
        except Exception as e:
            print(f"❌ 失敗: {e}")
    else:
        print("✓ shelves.enabled 欄位已存在")
    
    # 提交更改
    conn.commit()
    
    # 顯示當前 shelves 表結構
    print("\n" + "=" * 60)
    print("當前 shelves 表結構:")
    print("=" * 60)
    cursor.execute("PRAGMA table_info(shelves)")
    for row in cursor.fetchall():
        col_id, col_name, col_type, not_null, default_val, pk = row
        nullable = "NOT NULL" if not_null else "NULL"
        default = f"DEFAULT {default_val}" if default_val else ""
        pk_marker = "PRIMARY KEY" if pk else ""
        print(f"  {col_name:20s} {col_type:10s} {nullable:10s} {default:20s} {pk_marker}")
    
    conn.close()
    
    # 總結
    print("\n" + "=" * 60)
    if migrations_done:
        print("✅ 遷移完成！")
        print("\n執行的遷移:")
        for migration in migrations_done:
            print(f"  {migration}")
    else:
        print("✓ 數據庫已是最新版本，無需遷移")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = migrate_database()
    
    if success:
        print("\n🎉 數據庫遷移成功！")
        print("\n下一步:")
        print("  1. 重啟 Web UI 服務")
        print("  2. 在貨架管理頁面點擊「查看貨架配置」")
        print("  3. 啟用/停用貨架功能應該可以正常使用了")
    else:
        print("\n❌ 數據庫遷移失敗")
        exit(1)

