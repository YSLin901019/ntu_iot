#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據分析模塊
處理感測器數據分析和判斷邏輯
"""

from typing import Tuple
from config import OCCUPIED_THRESHOLD, SHELF_CONFIG
from database import get_shelf_max_distance

def analyze_shelf_data(shelf_id: str, distance_cm: float) -> Tuple[bool, float]:
    """
    分析貨架數據（單感測器模式）
    
    參數:
        shelf_id: 貨架 ID
        distance_cm: 測量距離（公分）
    
    返回:
        (occupied, fill_percent): 占用狀態和填充率
    
    判斷邏輯：
        - 距離越小 = 物品越多
        - 填充率 = (最大距離 - 實際距離) / 最大距離 × 100%
        - 當占用空間 > OCCUPIED_THRESHOLD 時判定為有物品
    """
    # 從資料庫獲取貨架配置
    max_distance = get_shelf_max_distance(shelf_id)
    
    if max_distance is None:
        # 如果資料庫沒有配置，使用預設配置
        if shelf_id in SHELF_CONFIG:
            max_distance = SHELF_CONFIG[shelf_id]["max_distance"]
        else:
            return False, 0.0
    
    # 計算物品佔用的空間（公分）
    occupied_space = max_distance - distance_cm
    
    # 判斷是否有物品
    # 占用空間 > OCCUPIED_THRESHOLD 就算有物品
    if occupied_space > OCCUPIED_THRESHOLD:
        occupied = True
        fill_percent = (occupied_space / max_distance) * 100.0
        
        # 限制在 0-100%
        fill_percent = max(0.0, min(100.0, fill_percent))
    else:
        occupied = False
        fill_percent = 0.0
    
    return occupied, fill_percent

def is_valid_distance(distance_cm: float) -> bool:
    """
    檢查距離數據是否有效
    
    參數:
        distance_cm: 測量距離
    
    返回:
        bool: 數據是否有效
    """
    return distance_cm >= 0

def calculate_stock_from_distance(distance_cm: float, product_length: float, max_distance: float) -> int:
    """
    根據距離和商品長度計算大約的庫存數量
    
    參數:
        distance_cm: 測量距離
        product_length: 商品長度
        max_distance: 貨架最大深度
    
    返回:
        int: 估計的庫存數量
    """
    if product_length <= 0:
        return 0
    
    occupied_space = max_distance - distance_cm
    estimated_count = int(occupied_space / product_length)
    
    return max(0, estimated_count)

def format_uptime(uptime_ms: int) -> str:
    """
    將運行時間從毫秒轉換為可讀格式
    
    參數:
        uptime_ms: 運行時間（毫秒）
    
    返回:
        str: 格式化的時間字串 (HH:MM:SS)
    """
    uptime_seconds = uptime_ms / 1000
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

