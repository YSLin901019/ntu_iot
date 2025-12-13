#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
貨架配置管理模塊
通過 MQTT 查詢 ESP32S3 的貨架配置並管理啟用狀態
"""

import json
import time
import threading
import paho.mqtt.client as mqtt
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE,
    TOPIC_SHELF_CONFIG_REQUEST, TOPIC_SHELF_CONFIG_RESPONSE,
    SHELF_CONFIG_TIMEOUT
)

class ShelfConfigManager:
    """貨架配置管理器"""
    
    def __init__(self):
        self.client = None
        self.response_data = None
        self.response_received = threading.Event()
        self.connected = threading.Event()
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連線回調"""
        if rc == 0:
            print(f"[ShelfConfig] 已連接到 MQTT Broker")
            # 訂閱貨架配置回應主題
            client.subscribe(TOPIC_SHELF_CONFIG_RESPONSE)
            print(f"[ShelfConfig] 已訂閱主題: {TOPIC_SHELF_CONFIG_RESPONSE}")
            # 標記連接完成
            self.connected.set()
        else:
            print(f"[ShelfConfig] 連接失敗，錯誤碼: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息回調"""
        try:
            payload = msg.payload.decode('utf-8')
            print(f"[ShelfConfig] 收到貨架配置: {payload}")
            
            self.response_data = json.loads(payload)
            self.response_received.set()
        except Exception as e:
            print(f"[ShelfConfig] 解析貨架配置失敗: {e}")
    
    def query_shelf_config(self, device_id, timeout=SHELF_CONFIG_TIMEOUT):
        """
        查詢指定設備的貨架配置
        
        Args:
            device_id: 設備 ID
            timeout: 超時時間（秒）
            
        Returns:
            dict: 貨架配置資訊，格式：
            {
                'device_id': 'ESP32S3_XXX',
                'shelves': [
                    {'shelf_id': 'A1', 'index': 0, 'gpio': 4, 'enabled': True},
                    ...
                ],
                'total_count': 12,
                'enabled_count': 2
            }
            如果超時或失敗則返回 None
        """
        print(f"[ShelfConfig] 正在查詢設備 {device_id} 的貨架配置...")
        
        # 重置回應
        self.response_data = None
        self.response_received.clear()
        self.connected.clear()
        
        # 創建 MQTT 客戶端
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        try:
            # 連接到 MQTT Broker
            print(f"[ShelfConfig] 正在連接到 {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            
            # 等待連接建立和訂閱完成
            if not self.connected.wait(3):
                print(f"[ShelfConfig] 連接超時")
                return None
            
            print(f"[ShelfConfig] 連接已建立，等待 0.5 秒確保訂閱完成...")
            time.sleep(0.5)
            
            # 發送查詢請求
            request = json.dumps({"device_id": device_id})
            result = self.client.publish(TOPIC_SHELF_CONFIG_REQUEST, request)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[ShelfConfig] 已發送查詢請求: {request}")
            else:
                print(f"[ShelfConfig] 發送請求失敗，錯誤碼: {result.rc}")
                return None
            
            # 等待回應
            print(f"[ShelfConfig] 等待設備回應（超時 {timeout} 秒）...")
            if self.response_received.wait(timeout):
                print(f"[ShelfConfig] 成功獲取貨架配置")
                return self.response_data
            else:
                print(f"[ShelfConfig] 查詢超時（{timeout}秒），未收到設備回應")
                print(f"[ShelfConfig] 提示：請確認設備 {device_id} 在線且正常運行")
                return None
                
        except Exception as e:
            print(f"[ShelfConfig] 查詢失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                print(f"[ShelfConfig] 已斷開 MQTT 連接")


def query_device_shelf_config(device_id, timeout=SHELF_CONFIG_TIMEOUT):
    """
    便捷函數：查詢設備的貨架配置
    
    Args:
        device_id: 設備 ID
        timeout: 超時時間（秒）
        
    Returns:
        dict: 貨架配置資訊，失敗返回 None
    """
    manager = ShelfConfigManager()
    return manager.query_shelf_config(device_id, timeout)


if __name__ == "__main__":
    # 測試
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python shelf_config_manager.py <device_id>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    config = query_device_shelf_config(device_id)
    
    if config:
        print(f"\n設備 {config['device_id']} 的貨架配置:")
        print(f"貨架總數: {config['total_count']}")
        print(f"已啟用數: {config['enabled_count']}")
        print("\n貨架列表:")
        for shelf in config['shelves']:
            status = "✓ 已啟用" if shelf['enabled'] else "✗ 停用"
            print(f"  [{shelf['shelf_id']}] GPIO:{shelf['gpio']} - {status}")
    else:
        print(f"查詢設備 {device_id} 失敗")

