#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
存放系統配置參數
"""

# ==================== MQTT 設定 ====================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# MQTT 主題
TOPIC_SENSOR = "shelf/sensor"
TOPIC_STATUS = "shelf/status"
TOPIC_COMMAND = "shelf/command"
TOPIC_DISCOVERY = "shelf/discovery"        # 設備探測請求
TOPIC_DISCOVERY_RESPONSE = "shelf/discovery/response"  # 設備探測回應
TOPIC_HEARTBEAT = "shelf/heartbeat"        # 心跳檢測請求
TOPIC_HEARTBEAT_RESPONSE = "shelf/heartbeat/response"  # 心跳檢測回應
TOPIC_SHELF_CONFIG_REQUEST = "shelf/config/request"    # 貨架配置查詢請求
TOPIC_SHELF_CONFIG_RESPONSE = "shelf/config/response"  # 貨架配置查詢回應

# ==================== 設備探測設定 ====================
DISCOVERY_TIMEOUT = 5  # 設備探測超時時間（秒）

# ==================== 心跳檢測設定 ====================
HEARTBEAT_INTERVAL = 30  # 心跳檢測間隔（秒）
HEARTBEAT_TIMEOUT = 5    # 心跳檢測超時（秒）

# ==================== 貨架配置查詢設定 ====================
SHELF_CONFIG_TIMEOUT = 5  # 貨架配置查詢超時時間（秒）

# ==================== 數據庫設定 ====================
DB_FILE = "shelf_data.db"

# ==================== 貨架配置 ====================
# 預設貨架尺寸配置（單感測器模式）
SHELF_CONFIG = {
    "A1": {"max_distance": 30.0},
    "A2": {"max_distance": 30.0},
    "B1": {"max_distance": 20.0}
}

# ==================== 判斷閾值 ====================
# 距離閾值：檢測距離小於最大距離 N cm 以上就判定為有貨
OCCUPIED_THRESHOLD = 2.0  # 公分

# ==================== 顏色代碼 ====================
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

