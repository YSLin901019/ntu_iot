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
            gpio INTEGER,
            enabled INTEGER DEFAULT 0,
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
    """
    初始化預設數據（已停用）
    
    注意：此函數已停用，不再自動創建測試設備。
    所有設備應通過 Web UI 的「設備探測」功能添加。
    """
    print(f"\n{Colors.WARNING}[初始化]{Colors.ENDC} init_default_data() 已停用")
    print(f"{Colors.WARNING}[提示]{Colors.ENDC} 請使用 Web UI 的設備探測功能添加設備")
    pass

# ==================== 貨架啟用狀態管理 ====================
def update_shelf_enabled_status(shelf_id: str, enabled: bool) -> bool:
    """
    更新貨架的啟用狀態
    
    Args:
        shelf_id: 貨架 ID
        enabled: 啟用狀態 (True/False)
        
    Returns:
        bool: 更新成功返回 True，失敗返回 False
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE shelves 
            SET enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE shelf_id = ?
        ''', (1 if enabled else 0, shelf_id))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            status_text = "啟用" if enabled else "停用"
            print(f"{Colors.OKGREEN}[成功]{Colors.ENDC} 貨架 {shelf_id} 已{status_text}")
            return True
        else:
            print(f"{Colors.WARNING}[警告]{Colors.ENDC} 找不到貨架 {shelf_id}")
            return False
            
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 更新貨架啟用狀態失敗: {e}")
        return False

def sync_shelf_config_from_esp32(device_id: str, shelf_config_list: List[Dict]) -> bool:
    """
    同步 ESP32S3 回傳的貨架配置到數據庫
    
    Args:
        device_id: 設備 ID
        shelf_config_list: 貨架配置列表，格式:
            [
                {'shelf_id': 'A1', 'index': 0, 'gpio': 4, 'enabled': True},
                {'shelf_id': 'A2', 'index': 1, 'gpio': 5, 'enabled': False},
                ...
            ]
            
    Returns:
        bool: 同步成功返回 True，失敗返回 False
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        for shelf_config in shelf_config_list:
            shelf_id = shelf_config['shelf_id']
            gpio = shelf_config.get('gpio')
            enabled = 1 if shelf_config.get('enabled', False) else 0
            position_index = shelf_config.get('index', 0)
            
            # 檢查貨架是否存在
            cursor.execute('SELECT shelf_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新現有貨架的 GPIO 和啟用狀態
                cursor.execute('''
                    UPDATE shelves 
                    SET gpio = ?, enabled = ?, position_index = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE shelf_id = ?
                ''', (gpio, enabled, position_index, shelf_id))
            else:
                # 創建新貨架（使用預設 max_distance）
                cursor.execute('''
                    INSERT INTO shelves 
                    (shelf_id, device_id, max_distance, gpio, enabled, position_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (shelf_id, device_id, 30.0, gpio, enabled, position_index))
        
        conn.commit()
        conn.close()
        
        print(f"{Colors.OKGREEN}[成功]{Colors.ENDC} 已同步設備 {device_id} 的 {len(shelf_config_list)} 個貨架配置")
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 同步貨架配置失敗: {e}")
        return False

def get_enabled_shelves(device_id: Optional[str] = None) -> List[Dict]:
    """
    獲取所有啟用的貨架
    
    Args:
        device_id: 可選，指定設備 ID 則只返回該設備的啟用貨架
        
    Returns:
        List[Dict]: 啟用的貨架列表
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT * FROM shelves 
                WHERE device_id = ? AND enabled = 1
                ORDER BY position_index
            ''', (device_id,))
        else:
            cursor.execute('''
                SELECT * FROM shelves 
                WHERE enabled = 1
                ORDER BY device_id, position_index
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢啟用貨架失敗: {e}")
        return []

def get_available_shelves_for_product(location: Optional[str] = None) -> List[Dict]:
    """
    獲取可用於商品配置的貨架（必須是啟用且未綁定商品的貨架）
    
    Args:
        location: 可選，指定區域則只返回該區域的可用貨架
        
    Returns:
        List[Dict]: 可用貨架列表
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if location:
            cursor.execute('''
                SELECT s.*, d.location, d.device_name, d.status
                FROM shelves s
                JOIN devices d ON s.device_id = d.device_id
                WHERE s.enabled = 1 
                  AND s.product_id IS NULL
                  AND d.location = ?
                ORDER BY s.device_id, s.position_index
            ''', (location,))
        else:
            cursor.execute('''
                SELECT s.*, d.location, d.device_name, d.status
                FROM shelves s
                JOIN devices d ON s.device_id = d.device_id
                WHERE s.enabled = 1 
                  AND s.product_id IS NULL
                ORDER BY d.location, s.device_id, s.position_index
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 查詢可用貨架失敗: {e}")
        return []


