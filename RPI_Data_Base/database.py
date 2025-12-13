#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據庫操作模塊
處理所有與 SQLite 數據庫相關的操作
"""

import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple
from config import DB_FILE, Colors, SHELF_CONFIG

# ==================== 數據庫初始化 ====================
def init_database():
    """初始化 SQLite 數據庫 - 支援多設備多貨架架構"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 設備表 (devices) - 存儲所有 ESP32 設備資訊
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            device_name TEXT,
            location TEXT,
            status TEXT DEFAULT 'offline',
            last_seen DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. 商品表 (products) - 存儲商品資訊
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            product_length REAL NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. 貨架配置表 (shelves) - 存儲貨架配置和商品綁定資訊
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shelves (
            shelf_id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            product_id TEXT,
            product_name TEXT,
            product_length REAL,
            max_distance REAL NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            position_index INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(device_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    ''')
    
    # 4. 感測器數據表 (sensor_data) - 存儲實時感測器數據
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            shelf_id TEXT NOT NULL,
            distance_cm REAL NOT NULL,
            occupied INTEGER NOT NULL,
            fill_percent REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(device_id),
            FOREIGN KEY (shelf_id) REFERENCES shelves(shelf_id)
        )
    ''')
    
    # 5. 庫存變動記錄表 (stock_changes) - 記錄庫存變化
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shelf_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            change_type TEXT NOT NULL,
            quantity_before INTEGER,
            quantity_after INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shelf_id) REFERENCES shelves(shelf_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    ''')
    
    # 建立索引以加速查詢
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_id ON sensor_data(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shelf_id ON sensor_data(shelf_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shelves_device ON shelves(device_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shelves_product ON shelves(product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_changes_shelf ON stock_changes(shelf_id)')
    
    conn.commit()
    conn.close()
    
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} 數據庫初始化完成: {DB_FILE}")
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} ✓ 設備表 (devices)")
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} ✓ 商品表 (products)")
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} ✓ 貨架配置表 (shelves)")
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} ✓ 感測器數據表 (sensor_data)")
    print(f"{Colors.OKGREEN}[數據庫]{Colors.ENDC} ✓ 庫存變動記錄表 (stock_changes)")

# ==================== 設備操作 ====================
def register_device(device_id: str, device_name: str = None, location: str = None) -> bool:
    """註冊或更新設備資訊"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO devices (device_id, device_name, location, status, last_seen)
            VALUES (?, ?, ?, 'online', CURRENT_TIMESTAMP)
        ''', (device_id, device_name or device_id, location))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 註冊設備失敗: {e}")
        return False

def update_device_last_seen(device_id: str):
    """更新設備最後上線時間"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE devices 
            SET last_seen = CURRENT_TIMESTAMP, status = 'online'
            WHERE device_id = ?
        ''', (device_id,))
        
        conn.commit()
        conn.close()
    except Exception:
        pass

def list_all_devices() -> List[Dict]:
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
            ORDER BY d.last_seen DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢設備失敗: {e}")
        return []

# ==================== 貨架操作 ====================
def register_shelf(shelf_id: str, device_id: str, max_distance: float, 
                   product_id: str = None, product_name: str = None, 
                   product_length: float = None, stock_quantity: int = 0, 
                   position_index: int = None) -> bool:
    """註冊或更新貨架配置"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO shelves 
            (shelf_id, device_id, product_id, product_name, product_length, 
             max_distance, stock_quantity, position_index, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (shelf_id, device_id, product_id, product_name, product_length, 
              max_distance, stock_quantity, position_index))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 註冊貨架失敗: {e}")
        return False

def get_shelf_max_distance(shelf_id: str) -> Optional[float]:
    """獲取貨架的最大距離配置"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('SELECT max_distance FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    except Exception:
        return None

def get_shelf_info(shelf_id: str) -> Optional[Dict]:
    """獲取完整的貨架資訊"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, d.device_name, d.location 
            FROM shelves s
            LEFT JOIN devices d ON s.device_id = d.device_id
            WHERE s.shelf_id = ?
        ''', (shelf_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 獲取貨架資訊失敗: {e}")
        return None

def list_all_shelves(device_id: str = None) -> List[Dict]:
    """列出所有貨架"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT s.*, d.device_name, d.location
                FROM shelves s
                LEFT JOIN devices d ON s.device_id = d.device_id
                WHERE s.device_id = ?
                ORDER BY s.position_index, s.shelf_id
            ''', (device_id,))
        else:
            cursor.execute('''
                SELECT s.*, d.device_name, d.location
                FROM shelves s
                LEFT JOIN devices d ON s.device_id = d.device_id
                ORDER BY s.device_id, s.position_index, s.shelf_id
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢貨架失敗: {e}")
        return []

# ==================== 感測器數據操作 ====================
def save_sensor_data(device_id: str, shelf_id: str, distance_cm: float, 
                     occupied: bool, fill_percent: float) -> bool:
    """儲存感測器數據到數據庫"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 使用當前時間作為時間戳記
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO sensor_data 
            (device_id, shelf_id, distance_cm, occupied, fill_percent, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (device_id, shelf_id, distance_cm, int(occupied), fill_percent, current_time))
        
        conn.commit()
        conn.close()
        
        # 更新設備最後上線時間
        update_device_last_seen(device_id)
        
        return True
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 數據庫儲存失敗: {e}")
        return False

def query_latest_data(shelf_id: str = None, device_id: str = None, limit: int = 10) -> List[Dict]:
    """查詢最新數據"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if shelf_id:
            cursor.execute('''
                SELECT sd.*, s.product_name, s.stock_quantity
                FROM sensor_data sd
                LEFT JOIN shelves s ON sd.shelf_id = s.shelf_id
                WHERE sd.shelf_id = ?
                ORDER BY sd.timestamp DESC
                LIMIT ?
            ''', (shelf_id, limit))
        elif device_id:
            cursor.execute('''
                SELECT sd.*, s.product_name, s.stock_quantity
                FROM sensor_data sd
                LEFT JOIN shelves s ON sd.shelf_id = s.shelf_id
                WHERE sd.device_id = ?
                ORDER BY sd.timestamp DESC
                LIMIT ?
            ''', (device_id, limit))
        else:
            cursor.execute('''
                SELECT sd.*, s.product_name, s.stock_quantity
                FROM sensor_data sd
                LEFT JOIN shelves s ON sd.shelf_id = s.shelf_id
                ORDER BY sd.timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢數據失敗: {e}")
        return []

# ==================== 庫存操作 ====================
def update_stock_quantity(shelf_id: str, new_quantity: int, change_type: str = 'manual') -> bool:
    """更新庫存數量並記錄變化"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 獲取當前庫存
        cursor.execute('SELECT stock_quantity, product_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        
        if result:
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
                    VALUES (?, ?, ?, ?, ?)
                ''', (shelf_id, product_id, change_type, old_quantity, new_quantity))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 更新庫存失敗: {e}")
        return False

def get_stock_summary() -> List[Dict]:
    """獲取庫存總覽"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                product_id,
                product_name,
                product_length,
                COUNT(*) as shelf_count,
                SUM(stock_quantity) as total_stock
            FROM shelves
            WHERE product_id IS NOT NULL
            GROUP BY product_id
            ORDER BY product_name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢庫存失敗: {e}")
        return []

# ==================== 初始化預設數據 ====================
def init_default_data():
    """初始化預設數據（用於測試）"""
    print(f"\n{Colors.OKCYAN}[初始化]{Colors.ENDC} 正在載入預設配置...")
    
    # 註冊預設設備
    register_device("ESP32_001", "ESP32 設備 1", "倉庫 A 區")
    
    # 註冊預設貨架
    for shelf_id, config in SHELF_CONFIG.items():
        register_shelf(
            shelf_id=shelf_id,
            device_id="ESP32_001",
            max_distance=config["max_distance"],
            position_index=int(shelf_id[1:]) if len(shelf_id) > 1 else 0
        )
    
    print(f"{Colors.OKGREEN}[初始化]{Colors.ENDC} 預設配置已載入")

