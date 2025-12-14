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
        self.calibrate_response = None
        self.calibrate_received = threading.Event()
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連線回調"""
        if rc == 0:
            print(f"[ShelfConfig] 已連接到 MQTT Broker")
            # 訂閱貨架配置回應主題
            client.subscribe(TOPIC_SHELF_CONFIG_RESPONSE)
            print(f"[ShelfConfig] 已訂閱主題: {TOPIC_SHELF_CONFIG_RESPONSE}")
            # 訂閱校正回應主題
            client.subscribe("shelf/calibrate/response")
            print(f"[ShelfConfig] 已訂閱主題: shelf/calibrate/response")
            # 標記連接完成
            self.connected.set()
        else:
            print(f"[ShelfConfig] 連接失敗，錯誤碼: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息回調"""
        try:
            payload = msg.payload.decode('utf-8')
            
            if msg.topic == TOPIC_SHELF_CONFIG_RESPONSE:
                print(f"[ShelfConfig] 收到貨架配置: {payload}")
            self.response_data = json.loads(payload)
            self.response_received.set()
            elif msg.topic == "shelf/calibrate/response":
                print(f"[Calibrate] 收到校正結果: {payload}")
                self.calibrate_response = json.loads(payload)
                self.calibrate_received.set()
        except Exception as e:
            print(f"[ShelfConfig] 解析訊息失敗: {e}")
    
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
    
    def calibrate_shelf_internal(self, device_id, shelf_id, timeout=15):
        """
        校正指定貨架（測量空貨架長度）
        
        Args:
            device_id: 設備 ID
            shelf_id: 貨架 ID
            timeout: 超時時間（秒）
            
        Returns:
            dict: {'success': bool, 'shelf_length': float, 'error': str}
        """
        print(f"[Calibrate] 開始校正貨架 {shelf_id} (設備: {device_id})...")
        
        # 重置回應
        self.calibrate_response = None
        self.calibrate_received.clear()
        self.connected.clear()
        
        # 創建 MQTT 客戶端
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        try:
            # 連接到 MQTT Broker
            print(f"[Calibrate] 正在連接到 {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            
            # 等待連接建立
            if not self.connected.wait(3):
                return {'success': False, 'error': '連接 MQTT 超時'}
            
            time.sleep(0.5)  # 確保訂閱完成
            
            # 發送校正命令
            command = f"calibrate {shelf_id}"
            result = self.client.publish("shelf/command", command)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[Calibrate] 已發送校正命令: {command}")
            else:
                return {'success': False, 'error': f'發送命令失敗，錯誤碼: {result.rc}'}
            
            # 等待校正結果
            print(f"[Calibrate] 等待校正完成（超時 {timeout} 秒）...")
            if self.calibrate_received.wait(timeout):
                if self.calibrate_response:
                    if self.calibrate_response.get('success'):
                        length = self.calibrate_response.get('shelf_length', 0.0)
                        print(f"[Calibrate] 校正成功！長度: {length:.2f} cm")
                        
                        # 更新資料庫
                        from database import update_shelf_calibration
                        update_shelf_calibration(shelf_id, length)
                        
                        return {
                            'success': True,
                            'shelf_length': length
                        }
                    else:
                        return {
                            'success': False,
                            'error': '校正失敗：感測器未連接或讀值異常'
                        }
                else:
                    return {'success': False, 'error': '未收到校正結果'}
            else:
                return {'success': False, 'error': f'校正超時（{timeout}秒），請確認設備在線'}
                
        except Exception as e:
            print(f"[Calibrate] 校正失敗: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                print(f"[Calibrate] 已斷開 MQTT 連接")


def calibrate_shelf(device_id, shelf_id, timeout=15):
    """
    便捷函數：校正貨架
    
    Args:
        device_id: 設備 ID
        shelf_id: 貨架 ID
        timeout: 超時時間（秒）
        
    Returns:
        dict: {'success': bool, 'shelf_length': float, 'error': str}
    """
    manager = ShelfConfigManager()
    return manager.calibrate_shelf_internal(device_id, shelf_id, timeout)


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

