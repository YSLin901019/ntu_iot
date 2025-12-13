#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料庫管理工具
用於管理設備、貨架、商品和查詢數據
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_FILE = "shelf_data.db"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """打印標題"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

def add_device():
    """新增設備"""
    print_header("新增 ESP32 設備")
    
    device_id = input("請輸入設備 ID (例如: ESP32_001): ").strip()
    device_name = input("請輸入設備名稱 (例如: ESP32 設備 1): ").strip()
    location = input("請輸入設備位置 (例如: 倉庫 A 區): ").strip()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO devices (device_id, device_name, location, status)
            VALUES (?, ?, ?, 'offline')
        ''', (device_id, device_name, location))
        
        conn.commit()
        conn.close()
        
        print(f"{Colors.OKGREEN}✓ 設備新增成功！{Colors.ENDC}")
    except sqlite3.IntegrityError:
        print(f"{Colors.FAIL}✗ 設備 ID 已存在！{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}✗ 新增失敗: {e}{Colors.ENDC}")

def add_product():
    """新增商品"""
    print_header("新增商品")
    
    product_id = input("請輸入商品 ID (例如: P001): ").strip()
    product_name = input("請輸入商品名稱 (例如: 可口可樂): ").strip()
    product_length = float(input("請輸入商品長度 (cm): ").strip())
    description = input("請輸入商品描述 (可選): ").strip()
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (product_id, product_name, product_length, description)
            VALUES (?, ?, ?, ?)
        ''', (product_id, product_name, product_length, description or None))
        
        conn.commit()
        conn.close()
        
        print(f"{Colors.OKGREEN}✓ 商品新增成功！{Colors.ENDC}")
    except sqlite3.IntegrityError:
        print(f"{Colors.FAIL}✗ 商品 ID 已存在！{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}✗ 新增失敗: {e}{Colors.ENDC}")

def add_shelf():
    """新增貨架"""
    print_header("新增貨架")
    
    # 顯示可用設備
    list_devices()
    
    shelf_id = input("\n請輸入貨架 ID (例如: A1): ").strip()
    device_id = input("請輸入設備 ID: ").strip()
    max_distance = float(input("請輸入最大距離 (cm): ").strip())
    
    # 詢問是否綁定商品
    bind_product = input("是否綁定商品？(y/n): ").strip().lower() == 'y'
    
    product_id = None
    product_name = None
    product_length = None
    stock_quantity = 0
    
    if bind_product:
        list_products()
        product_id = input("\n請輸入商品 ID: ").strip()
        
        # 從資料庫獲取商品資訊
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT product_name, product_length FROM products WHERE product_id = ?', (product_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            product_name, product_length = result
            stock_quantity = int(input("請輸入初始庫存數量: ").strip())
        else:
            print(f"{Colors.WARNING}找不到商品 ID: {product_id}{Colors.ENDC}")
            return
    
    position_index = int(input("請輸入貨架位置索引 (數字): ").strip() or "0")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shelves 
            (shelf_id, device_id, product_id, product_name, product_length, 
             max_distance, stock_quantity, position_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (shelf_id, device_id, product_id, product_name, product_length, 
              max_distance, stock_quantity, position_index))
        
        conn.commit()
        conn.close()
        
        print(f"{Colors.OKGREEN}✓ 貨架新增成功！{Colors.ENDC}")
    except sqlite3.IntegrityError:
        print(f"{Colors.FAIL}✗ 貨架 ID 已存在！{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}✗ 新增失敗: {e}{Colors.ENDC}")

def list_devices():
    """列出所有設備"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, COUNT(s.shelf_id) as shelf_count
            FROM devices d
            LEFT JOIN shelves s ON d.device_id = s.device_id
            GROUP BY d.device_id
            ORDER BY d.device_id
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"{Colors.WARNING}沒有設備記錄{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}{'設備ID':<15} {'設備名稱':<20} {'位置':<15} {'狀態':<10} {'貨架數':<8}{Colors.ENDC}")
        print("-" * 70)
        
        for row in rows:
            status_color = Colors.OKGREEN if row['status'] == 'online' else Colors.FAIL
            print(f"{row['device_id']:<15} {row['device_name']:<20} {row['location'] or 'N/A':<15} "
                  f"{status_color}{row['status']:<10}{Colors.ENDC} {row['shelf_count']:<8}")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 查詢失敗: {e}{Colors.ENDC}")

def list_products():
    """列出所有商品"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM products ORDER BY product_id')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"{Colors.WARNING}沒有商品記錄{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}{'商品ID':<10} {'商品名稱':<20} {'長度(cm)':<10} {'描述':<30}{Colors.ENDC}")
        print("-" * 70)
        
        for row in rows:
            print(f"{row['product_id']:<10} {row['product_name']:<20} {row['product_length']:<10} {row['description'] or 'N/A':<30}")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 查詢失敗: {e}{Colors.ENDC}")

def list_shelves():
    """列出所有貨架"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, d.device_name
            FROM shelves s
            LEFT JOIN devices d ON s.device_id = d.device_id
            ORDER BY s.device_id, s.position_index, s.shelf_id
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"{Colors.WARNING}沒有貨架記錄{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}{'貨架ID':<8} {'設備ID':<12} {'商品名稱':<15} {'最大距離':<10} {'庫存':<6} {'位置':<6}{Colors.ENDC}")
        print("-" * 70)
        
        for row in rows:
            print(f"{row['shelf_id']:<8} {row['device_id']:<12} {row['product_name'] or 'N/A':<15} "
                  f"{row['max_distance']:<10} {row['stock_quantity']:<6} {row['position_index'] or 'N/A':<6}")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 查詢失敗: {e}{Colors.ENDC}")

def view_sensor_data():
    """查看感測器數據"""
    print_header("查看感測器數據")
    
    print("1. 查看所有數據")
    print("2. 查看特定貨架數據")
    print("3. 查看特定設備數據")
    
    choice = input("\n請選擇 (1-3): ").strip()
    limit = int(input("顯示筆數 (預設 10): ").strip() or "10")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if choice == "2":
            shelf_id = input("請輸入貨架 ID: ").strip()
            cursor.execute('''
                SELECT * FROM sensor_data
                WHERE shelf_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (shelf_id, limit))
        elif choice == "3":
            device_id = input("請輸入設備 ID: ").strip()
            cursor.execute('''
                SELECT * FROM sensor_data
                WHERE device_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (device_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM sensor_data
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"{Colors.WARNING}沒有數據記錄{Colors.ENDC}")
            return
        
        print(f"\n{Colors.BOLD}{'時間':<20} {'設備ID':<12} {'貨架ID':<8} {'距離':<8} {'占用':<6} {'填充率':<8}{Colors.ENDC}")
        print("-" * 70)
        
        for row in rows:
            occupied_text = "是" if row['occupied'] else "否"
            occupied_color = Colors.OKGREEN if row['occupied'] else Colors.WARNING
            print(f"{row['timestamp']:<20} {row['device_id']:<12} {row['shelf_id']:<8} "
                  f"{row['distance_cm']:<8.1f} {occupied_color}{occupied_text:<6}{Colors.ENDC} {row['fill_percent']:<8.1f}%")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 查詢失敗: {e}{Colors.ENDC}")

def update_stock():
    """更新庫存"""
    print_header("更新庫存")
    
    list_shelves()
    
    shelf_id = input("\n請輸入貨架 ID: ").strip()
    new_quantity = int(input("請輸入新的庫存數量: ").strip())
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 獲取當前庫存
        cursor.execute('SELECT stock_quantity, product_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        
        if not result:
            print(f"{Colors.FAIL}✗ 找不到貨架 ID: {shelf_id}{Colors.ENDC}")
            conn.close()
            return
        
        old_quantity, product_id = result
        
        # 更新庫存
        cursor.execute('''
            UPDATE shelves 
            SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE shelf_id = ?
        ''', (new_quantity, shelf_id))
        
        # 記錄變化
        if product_id:
            cursor.execute('''
                INSERT INTO stock_changes 
                (shelf_id, product_id, change_type, quantity_before, quantity_after)
                VALUES (?, ?, 'manual', ?, ?)
            ''', (shelf_id, product_id, old_quantity, new_quantity))
        
        conn.commit()
        conn.close()
        
        print(f"{Colors.OKGREEN}✓ 庫存更新成功！{Colors.ENDC}")
        print(f"  貨架: {shelf_id}")
        print(f"  原庫存: {old_quantity}")
        print(f"  新庫存: {new_quantity}")
        print(f"  變化: {new_quantity - old_quantity:+d}")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 更新失敗: {e}{Colors.ENDC}")

def show_statistics():
    """顯示統計資訊"""
    print_header("系統統計")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 設備統計
        cursor.execute('SELECT COUNT(*) FROM devices')
        device_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'online'")
        online_devices = cursor.fetchone()[0]
        
        # 貨架統計
        cursor.execute('SELECT COUNT(*) FROM shelves')
        shelf_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM shelves WHERE product_id IS NOT NULL')
        shelves_with_products = cursor.fetchone()[0]
        
        # 商品統計
        cursor.execute('SELECT COUNT(*) FROM products')
        product_count = cursor.fetchone()[0]
        
        # 庫存總計
        cursor.execute('SELECT SUM(stock_quantity) FROM shelves')
        total_stock = cursor.fetchone()[0] or 0
        
        # 數據統計
        cursor.execute('SELECT COUNT(*) FROM sensor_data')
        data_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM sensor_data WHERE occupied = 1')
        occupied_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"{Colors.OKBLUE}[設備]{Colors.ENDC}")
        print(f"  總設備數: {device_count}")
        print(f"  在線設備: {Colors.OKGREEN}{online_devices}{Colors.ENDC}")
        print(f"  離線設備: {Colors.FAIL}{device_count - online_devices}{Colors.ENDC}")
        
        print(f"\n{Colors.OKBLUE}[貨架]{Colors.ENDC}")
        print(f"  總貨架數: {shelf_count}")
        print(f"  已配置商品: {shelves_with_products}")
        print(f"  未配置商品: {shelf_count - shelves_with_products}")
        
        print(f"\n{Colors.OKBLUE}[商品與庫存]{Colors.ENDC}")
        print(f"  商品種類: {product_count}")
        print(f"  總庫存量: {total_stock}")
        
        print(f"\n{Colors.OKBLUE}[感測器數據]{Colors.ENDC}")
        print(f"  總記錄數: {data_count}")
        print(f"  占用記錄: {occupied_count}")
        print(f"  空置記錄: {data_count - occupied_count}")
        if data_count > 0:
            print(f"  占用率: {occupied_count / data_count * 100:.1f}%")
    
    except Exception as e:
        print(f"{Colors.FAIL}✗ 查詢失敗: {e}{Colors.ENDC}")

def main_menu():
    """主選單"""
    while True:
        print_header("資料庫管理工具")
        
        print(f"{Colors.OKCYAN}[設備管理]{Colors.ENDC}")
        print("  1. 新增設備")
        print("  2. 查看所有設備")
        
        print(f"\n{Colors.OKCYAN}[商品管理]{Colors.ENDC}")
        print("  3. 新增商品")
        print("  4. 查看所有商品")
        
        print(f"\n{Colors.OKCYAN}[貨架管理]{Colors.ENDC}")
        print("  5. 新增貨架")
        print("  6. 查看所有貨架")
        print("  7. 更新庫存")
        
        print(f"\n{Colors.OKCYAN}[數據查詢]{Colors.ENDC}")
        print("  8. 查看感測器數據")
        print("  9. 查看系統統計")
        
        print(f"\n  0. 退出")
        
        choice = input(f"\n{Colors.BOLD}請選擇功能 (0-9): {Colors.ENDC}").strip()
        
        if choice == "1":
            add_device()
        elif choice == "2":
            print_header("設備列表")
            list_devices()
        elif choice == "3":
            add_product()
        elif choice == "4":
            print_header("商品列表")
            list_products()
        elif choice == "5":
            add_shelf()
        elif choice == "6":
            print_header("貨架列表")
            list_shelves()
        elif choice == "7":
            update_stock()
        elif choice == "8":
            view_sensor_data()
        elif choice == "9":
            show_statistics()
        elif choice == "0":
            print(f"\n{Colors.OKGREEN}再見！{Colors.ENDC}\n")
            break
        else:
            print(f"{Colors.FAIL}無效的選擇！{Colors.ENDC}")
        
        input(f"\n按 Enter 繼續...")

if __name__ == "__main__":
    main_menu()

