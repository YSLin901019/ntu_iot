#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫清理工具
自動清理舊的感測器數據，保持數據庫大小可控
"""

import sqlite3
import datetime
from config import DB_FILE, Colors

def clean_old_sensor_data(keep_days=7, keep_min_records=1000):
    """
    清理舊的感測器數據
    
    Args:
        keep_days: 保留最近幾天的數據（預設 7 天）
        keep_min_records: 至少保留多少筆記錄（預設 1000 筆）
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 檢查總記錄數
        cursor.execute('SELECT COUNT(*) FROM sensor_data')
        total_before = cursor.fetchone()[0]
        
        print(f"\n{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}數據庫清理工具{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}\n")
        print(f"清理前總記錄數: {total_before:,}")
        
        # 如果記錄數少於最小保留數，不清理
        if total_before <= keep_min_records:
            print(f"{Colors.WARNING}[提示]{Colors.ENDC} 記錄數({total_before})未超過最小保留數({keep_min_records})，無需清理")
            conn.close()
            return
        
        # 計算截止日期
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"保留天數: {keep_days} 天")
        print(f"截止時間: {cutoff_str}")
        
        # 檢查要刪除的記錄數
        cursor.execute('''
            SELECT COUNT(*) FROM sensor_data 
            WHERE timestamp < ?
        ''', (cutoff_str,))
        to_delete = cursor.fetchone()[0]
        
        # 確保刪除後至少保留 keep_min_records 筆
        records_after_delete = total_before - to_delete
        if records_after_delete < keep_min_records:
            to_delete = total_before - keep_min_records
            print(f"\n{Colors.WARNING}[調整]{Colors.ENDC} 為了保留最少 {keep_min_records} 筆記錄")
            print(f"實際刪除記錄數: {to_delete:,}")
            
            # 使用 LIMIT 刪除最舊的記錄
            cursor.execute('''
                DELETE FROM sensor_data 
                WHERE id IN (
                    SELECT id FROM sensor_data 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
            ''', (to_delete,))
        else:
            print(f"將刪除記錄數: {to_delete:,}")
            
            # 刪除舊數據
            cursor.execute('''
                DELETE FROM sensor_data 
                WHERE timestamp < ?
            ''', (cutoff_str,))
        
        conn.commit()
        
        # 檢查清理後的記錄數
        cursor.execute('SELECT COUNT(*) FROM sensor_data')
        total_after = cursor.fetchone()[0]
        
        # 優化數據庫
        print(f"\n{Colors.OKCYAN}[優化]{Colors.ENDC} 正在優化數據庫...")
        cursor.execute('VACUUM')
        
        conn.close()
        
        # 顯示結果
        print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[完成]{Colors.ENDC} 清理成功！")
        print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
        print(f"清理前: {total_before:,} 筆")
        print(f"清理後: {total_after:,} 筆")
        print(f"已刪除: {total_before - total_after:,} 筆")
        
        # 顯示數據庫大小變化
        import os
        size_mb = os.path.getsize(DB_FILE) / (1024*1024)
        print(f"當前數據庫大小: {size_mb:.2f} MB\n")
        
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 清理失敗: {e}")


def get_database_info():
    """顯示數據庫資訊"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 總記錄數
        cursor.execute('SELECT COUNT(*) FROM sensor_data')
        total = cursor.fetchone()[0]
        
        # 最舊記錄
        cursor.execute('SELECT MIN(timestamp) FROM sensor_data')
        oldest = cursor.fetchone()[0]
        
        # 最新記錄
        cursor.execute('SELECT MAX(timestamp) FROM sensor_data')
        newest = cursor.fetchone()[0]
        
        # 設備數
        cursor.execute('SELECT COUNT(DISTINCT device_id) FROM sensor_data')
        devices = cursor.fetchone()[0]
        
        # 貨架數
        cursor.execute('SELECT COUNT(DISTINCT shelf_id) FROM sensor_data')
        shelves = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n{Colors.OKCYAN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}數據庫資訊{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*60}{Colors.ENDC}\n")
        print(f"總記錄數: {total:,}")
        print(f"設備數量: {devices}")
        print(f"貨架數量: {shelves}")
        print(f"最舊記錄: {oldest}")
        print(f"最新記錄: {newest}")
        
        import os
        size_mb = os.path.getsize(DB_FILE) / (1024*1024)
        print(f"數據庫大小: {size_mb:.2f} MB\n")
        
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 獲取資訊失敗: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'info':
            # 只顯示資訊
            get_database_info()
        elif sys.argv[1] == 'clean':
            # 清理數據
            keep_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            keep_min = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
            
            get_database_info()
            print(f"\n{Colors.WARNING}準備清理舊數據...{Colors.ENDC}")
            response = input(f"確定要清理超過 {keep_days} 天的數據嗎？(y/N): ")
            
            if response.lower() == 'y':
                clean_old_sensor_data(keep_days, keep_min)
            else:
                print(f"{Colors.WARNING}[取消]{Colors.ENDC} 已取消清理")
        else:
            print("使用方法:")
            print("  查看資訊: python3 clean_database.py info")
            print("  清理數據: python3 clean_database.py clean [保留天數] [最少保留筆數]")
            print("\n例如:")
            print("  python3 clean_database.py info")
            print("  python3 clean_database.py clean 7 1000")
            print("  python3 clean_database.py clean 3 500")
    else:
        print("使用方法:")
        print("  查看資訊: python3 clean_database.py info")
        print("  清理數據: python3 clean_database.py clean [保留天數] [最少保留筆數]")
        print("\n例如:")
        print("  python3 clean_database.py info")
        print("  python3 clean_database.py clean 7 1000")
        print("  python3 clean_database.py clean 3 500")

