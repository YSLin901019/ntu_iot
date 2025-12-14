#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫遷移：新增貨架校正相關欄位
- shelf_length: 貨架總長度（透過校正獲得）
- sensor_connected: 感測器連接狀態（由 ESP32 自動偵測）
"""

import sqlite3
from config import DB_FILE, Colors

def migrate():
    """執行遷移"""
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}數據庫遷移：新增貨架校正相關欄位{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 檢查欄位是否已存在
        cursor.execute("PRAGMA table_info(shelves)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 新增 shelf_length 欄位
        if 'shelf_length' not in columns:
            print(f"{Colors.OKCYAN}[遷移]{Colors.ENDC} 正在新增 shelf_length 欄位...")
            cursor.execute('ALTER TABLE shelves ADD COLUMN shelf_length REAL DEFAULT 0.0')
            print(f"{Colors.OKGREEN}[遷移]{Colors.ENDC} ✓ shelf_length 欄位新增成功")
        else:
            print(f"{Colors.WARNING}[遷移]{Colors.ENDC} shelf_length 欄位已存在，跳過")
        
        # 新增 sensor_connected 欄位
        if 'sensor_connected' not in columns:
            print(f"{Colors.OKCYAN}[遷移]{Colors.ENDC} 正在新增 sensor_connected 欄位...")
            cursor.execute('ALTER TABLE shelves ADD COLUMN sensor_connected INTEGER DEFAULT 0')
            print(f"{Colors.OKGREEN}[遷移]{Colors.ENDC} ✓ sensor_connected 欄位新增成功")
        else:
            print(f"{Colors.WARNING}[遷移]{Colors.ENDC} sensor_connected 欄位已存在，跳過")
        
        conn.commit()
        conn.close()
        
        print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[成功]{Colors.ENDC} 遷移完成！")
        print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
        
        return True
        
    except Exception as e:
        print(f"\n{Colors.FAIL}[錯誤]{Colors.ENDC} 遷移失敗: {e}")
        return False

if __name__ == "__main__":
    migrate()


