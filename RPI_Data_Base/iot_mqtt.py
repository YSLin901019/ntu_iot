#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT 通信模塊
負責接收和發送 MQTT 數據和指令
"""

import paho.mqtt.client as mqtt
import json
import datetime

# 導入自定義模塊
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE,
    TOPIC_SENSOR, TOPIC_STATUS, TOPIC_COMMAND,
    Colors
)
from database import (
    init_database, init_default_data,
    register_device, save_sensor_data, get_shelf_info,
    update_shelf_calibration, update_shelf_config
)
from analyzer import analyze_shelf_data, is_valid_distance, format_uptime

# 嘗試導入 Firebase 模塊（可選）
try:
    import iot_firebase_pb
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False

# ==================== MQTT 回調函式 ====================
def on_connect(client, userdata, flags, rc):
    """當連接到 MQTT broker 時的回調"""
    if rc == 0:
        print(f"{Colors.OKGREEN}[MQTT]{Colors.ENDC} 已連接到 MQTT Broker")
        
        # 訂閱主題
        client.subscribe(TOPIC_SENSOR)
        print(f"{Colors.OKCYAN}[訂閱]{Colors.ENDC} {TOPIC_SENSOR}")
        
        client.subscribe(TOPIC_STATUS)
        print(f"{Colors.OKCYAN}[訂閱]{Colors.ENDC} {TOPIC_STATUS}")
        
        # 訂閱貨架校正回應主題
        client.subscribe("shelf/calibrate/response")
        print(f"{Colors.OKCYAN}[訂閱]{Colors.ENDC} shelf/calibrate/response")
        
        # 訂閱貨架配置回應主題
        client.subscribe("shelf/config/response")
        print(f"{Colors.OKCYAN}[訂閱]{Colors.ENDC} shelf/config/response")
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}RPI 數據處理中心已啟動{Colors.ENDC}")
        print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    else:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 連線失敗，錯誤碼: {rc}")

def on_disconnect(client, userdata, rc):
    """當 MQTT 斷線時的回調"""
    if rc != 0:
        print(f"{Colors.WARNING}[警告]{Colors.ENDC} 非預期斷線，將自動重連...")

def on_message(client, userdata, msg):
    """當收到訊息時的回調"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    if topic == TOPIC_SENSOR:
        handle_sensor_message(payload, timestamp)
    elif topic == TOPIC_STATUS:
        handle_status_message(payload, timestamp)
    elif topic == "shelf/calibrate/response":
        handle_calibrate_response(payload, timestamp)
    elif topic == "shelf/config/response":
        handle_config_response(payload, timestamp)

# ==================== 感測器數據處理 ====================
def handle_sensor_message(payload: str, timestamp: str):
    """處理感測器數據訊息"""
    try:
        # 解析 JSON 數據
        data = json.loads(payload)
        
        device_id = data.get('device_id', 'N/A')
        shelf_id = data.get('shelf_id', 'N/A')
        distance_cm = data.get('distance_cm', -1)
        
        # 檢查數據是否有效
        if not is_valid_distance(distance_cm):
            print(f"\n{Colors.HEADER}[{timestamp}]{Colors.ENDC}")
            print(f"{Colors.WARNING}[無效數據]{Colors.ENDC} 設備: {device_id}, 貨架: {Colors.BOLD}{shelf_id}{Colors.ENDC}")
            print(f"  距離: {Colors.FAIL}{distance_cm} cm (無效){Colors.ENDC}")
            print(f"  原因: 感測器讀取失敗或超出範圍")
            print(f"  ✗ 此筆數據已忽略，不儲存到數據庫")
            return
        
        # 分析數據
        occupied, fill_percent = analyze_shelf_data(shelf_id, distance_cm)
        
        # 儲存到數據庫
        save_sensor_data(device_id, shelf_id, distance_cm, occupied, fill_percent)
        
        # 獲取貨架資訊
        shelf_info = get_shelf_info(shelf_id)
        
        # 顯示結果
        print_sensor_data(timestamp, device_id, shelf_id, distance_cm, 
                         occupied, fill_percent, shelf_info)
        
        # 上傳到 Firebase（如果啟用）
        if FIREBASE_ENABLED:
            try:
                iot_firebase_pb.upload_sensor_data(device_id, shelf_id, 
                                                   distance_cm, occupied, fill_percent)
            except Exception:
                pass  # Firebase 上傳失敗不影響本地儲存
        
    except json.JSONDecodeError as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} JSON 解析失敗: {e}")
        print(f"  原始數據: {payload}")
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 處理數據失敗: {e}")

def print_sensor_data(timestamp: str, device_id: str, shelf_id: str, 
                      distance_cm: float, occupied: bool, fill_percent: float, 
                      shelf_info: dict = None):
    """格式化顯示感測器數據"""
    print(f"\n{Colors.HEADER}[{timestamp}]{Colors.ENDC}")
    print(f"{Colors.OKBLUE}[感測器數據]{Colors.ENDC}")
    print(f"  設備ID: {Colors.BOLD}{device_id}{Colors.ENDC}")
    print(f"  貨架ID: {Colors.BOLD}{shelf_id}{Colors.ENDC}")
    
    # 顯示商品資訊（如果有）
    if shelf_info and shelf_info.get('product_name'):
        print(f"  商品名稱: {Colors.OKCYAN}{shelf_info['product_name']}{Colors.ENDC}")
        print(f"  商品ID: {shelf_info.get('product_id', 'N/A')}")
        print(f"  商品長度: {shelf_info.get('product_length', 'N/A')} cm")
        print(f"  庫存數量: {shelf_info.get('stock_quantity', 0)}")
    
    print(f"  距離: {distance_cm:.1f} cm")
    
    if occupied:
        print(f"  狀態: {Colors.OKGREEN}有物品{Colors.ENDC}")
        print(f"  填充率: {Colors.OKGREEN}{fill_percent:.1f}%{Colors.ENDC}")
    else:
        print(f"  狀態: {Colors.WARNING}空的{Colors.ENDC}")
        print(f"  填充率: 0%")
    
    print(f"  ✓ 已儲存到數據庫")

# ==================== 狀態訊息處理 ====================
def handle_status_message(payload: str, timestamp: str):
    """處理狀態訊息"""
    print(f"\n{Colors.HEADER}[{timestamp}]{Colors.ENDC}")
    print(f"{Colors.OKBLUE}[ESP32 狀態]{Colors.ENDC}")
    
    try:
        data = json.loads(payload)
        device_id = data.get('device_id', 'unknown')
        
        print(f"  設備ID: {device_id}")
        print(f"  WiFi: {data.get('wifi', 'N/A')}")
        print(f"  MQTT: {data.get('mqtt', 'N/A')}")
        
        # 格式化運行時間
        uptime_ms = data.get('uptime_ms', 0)
        if uptime_ms > 0:
            uptime_str = format_uptime(uptime_ms)
            print(f"  運行時間: {uptime_str}")
        
        print(f"  貨架數量: {data.get('shelf_count', 'N/A')}")
        
        # 註冊或更新設備（使用原始 device_id 作為設備名稱）
        register_device(device_id, device_name=device_id)
        
    except json.JSONDecodeError:
        print(f"  訊息: {payload}")

# ==================== 校正結果處理 ====================
def handle_calibrate_response(payload: str, timestamp: str):
    """處理貨架校正結果"""
    print(f"\n{Colors.HEADER}[{timestamp}]{Colors.ENDC}")
    print(f"{Colors.OKBLUE}[貨架校正]{Colors.ENDC}")
    
    try:
        data = json.loads(payload)
        device_id = data.get('device_id', 'unknown')
        shelf_id = data.get('shelf_id', 'N/A')
        success = data.get('success', False)
        shelf_length = data.get('shelf_length', 0.0)
        
        print(f"  設備ID: {device_id}")
        print(f"  貨架ID: {Colors.BOLD}{shelf_id}{Colors.ENDC}")
        
        if success:
            print(f"  校正結果: {Colors.OKGREEN}成功{Colors.ENDC}")
            print(f"  貨架長度: {Colors.OKGREEN}{shelf_length:.2f} cm{Colors.ENDC}")
            
            # 更新資料庫
            update_shelf_calibration(shelf_id, shelf_length)
            print(f"  ✓ 已更新到數據庫")
        else:
            print(f"  校正結果: {Colors.FAIL}失敗{Colors.ENDC}")
            print(f"  原因: 感測器未連接或讀值異常")
        
    except json.JSONDecodeError as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} JSON 解析失敗: {e}")
        print(f"  原始數據: {payload}")
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 處理校正結果失敗: {e}")

# ==================== 貨架配置響應處理 ====================
def handle_config_response(payload: str, timestamp: str):
    """處理貨架配置響應"""
    print(f"\n{Colors.HEADER}[{timestamp}]{Colors.ENDC}")
    print(f"{Colors.OKBLUE}[貨架配置更新]{Colors.ENDC}")
    
    try:
        data = json.loads(payload)
        device_id = data.get('device_id', 'unknown')
        shelves = data.get('shelves', [])
        
        print(f"  設備ID: {device_id}")
        print(f"  貨架數量: {len(shelves)}")
        
        # 更新每個貨架的配置到資料庫
        for shelf in shelves:
            shelf_id = shelf.get('shelf_id')
            enabled = shelf.get('enabled', False)
            sensor_connected = shelf.get('sensor_connected', False)
            shelf_length = shelf.get('shelf_length', 0.0)
            gpio = shelf.get('gpio', 0)
            
            # 更新資料庫
            update_shelf_config(
                device_id=device_id,
                shelf_id=shelf_id,
                enabled=enabled,
                sensor_connected=sensor_connected,
                shelf_length=shelf_length,
                gpio=gpio
            )
        
        print(f"  ✓ 已更新 {len(shelves)} 個貨架配置到數據庫")
        
    except json.JSONDecodeError as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} JSON 解析失敗: {e}")
        print(f"  原始數據: {payload}")
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 處理配置響應失敗: {e}")

# ==================== MQTT 命令發送 ====================
def send_command(client: mqtt.Client, command: str) -> bool:
    """
    發送命令到 ESP32
    
    參數:
        client: MQTT 客戶端
        command: 命令字串
    
    返回:
        bool: 是否成功發送
    """
    try:
        if client.is_connected():
            client.publish(TOPIC_COMMAND, command, qos=0)
            print(f"{Colors.OKGREEN}[命令]{Colors.ENDC} 已發送: {command}")
            return True
        else:
            print(f"{Colors.WARNING}[警告]{Colors.ENDC} MQTT 未連接，無法發送命令")
            return False
    except Exception as e:
        print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 發送命令失敗: {e}")
        return False

def request_system_status(client: mqtt.Client):
    """請求 ESP32 回報系統狀態"""
    return send_command(client, "status")

def request_all_data(client: mqtt.Client):
    """請求 ESP32 回報所有貨架數據"""
    return send_command(client, "data")

def request_shelf_data(client: mqtt.Client, shelf_id: str):
    """請求特定貨架的數據"""
    return send_command(client, f"shelf {shelf_id}")

# ==================== MQTT 客戶端管理 ====================
class MQTTClient:
    """MQTT 客戶端包裝類"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id="RPI_DataCenter")
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        self.connected = False
    
    def connect(self):
        """連接到 MQTT Broker"""
        try:
            print(f"正在連接到 MQTT Broker ({MQTT_BROKER}:{MQTT_PORT})...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.connected = True
            return True
        except Exception as e:
            print(f"{Colors.FAIL}[錯誤]{Colors.ENDC} 連接失敗: {e}")
            return False
    
    def start(self):
        """啟動 MQTT 客戶端（阻塞模式）"""
        if self.connect():
            print("提示：按 Ctrl+C 可以停止程式\n")
            try:
                self.client.loop_forever()
            except KeyboardInterrupt:
                print(f"\n\n{Colors.WARNING}[使用者中斷]{Colors.ENDC} 正在關閉...")
            finally:
                self.disconnect()
    
    def disconnect(self):
        """斷開 MQTT 連接"""
        self.client.disconnect()
        self.connected = False
        print(f"{Colors.OKGREEN}[已斷線]{Colors.ENDC} 程式結束")
    
    def send_command(self, command: str):
        """發送命令"""
        return send_command(self.client, command)

# ==================== 主程式 ====================
def main():
    """主程式進入點"""
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║       ESP32 貨架監控系統 - RPI 數據處理中心              ║")
    print("║           支援多設備多貨架架構                           ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # 初始化數據庫
    init_database()
    
    # 載入預設配置
    init_default_data()
    
    # 創建並啟動 MQTT 客戶端
    mqtt_client = MQTTClient()
    mqtt_client.start()

if __name__ == "__main__":
    main()
