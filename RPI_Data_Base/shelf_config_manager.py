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
            
            # ✅ 訂閱設備特定的校正回應主題
            if hasattr(self, 'current_device_id') and self.current_device_id:
                from config import get_device_calibrate_response_topic
                calibrate_topic = get_device_calibrate_response_topic(self.current_device_id)
                client.subscribe(calibrate_topic, qos=1)
                print(f"[ShelfConfig] 已訂閱校正回應主題: {calibrate_topic}")
            
            # 訂閱貨架配置回應主題（通配符模式支援多設備）
            client.subscribe("shelf/+/config/response", qos=1)
            print(f"[ShelfConfig] 已訂閱配置回應主題: shelf/+/config/response")
            
            # 標記連接完成
            time.sleep(1)  # 等待訂閱生效
            self.connected.set()
        else:
            print(f"[ShelfConfig] 連接失敗，錯誤碼: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息回調"""
        try:
            payload = msg.payload.decode('utf-8')
            topic = msg.topic
            
            print(f"[ShelfConfig] 收到訊息 [{topic}]: {payload[:100]}...")
            
            # ✅ 匹配設備特定的配置回應主題（使用通配符訂閱 shelf/+/config/response）
            if "/config/response" in topic:
                print(f"[ShelfConfig] ✓ 收到貨架配置回應")
                data = json.loads(payload)
                # 驗證設備ID是否匹配
                if hasattr(self, 'current_device_id') and self.current_device_id:
                    if data.get('device_id') == self.current_device_id:
                        self.response_data = data
                        self.response_received.set()
                    else:
                        print(f"[ShelfConfig] ⚠ 設備ID不匹配，忽略（期望: {self.current_device_id}, 收到: {data.get('device_id')}）")
                else:
                    self.response_data = data
                    self.response_received.set()
            # ✅ 匹配設備特定的校正回應主題
            elif "/calibrate/response" in topic:
                print(f"[Calibrate] ✓ 收到校正結果")
                data = json.loads(payload)
                # 驗證設備ID是否匹配
                if hasattr(self, 'current_device_id') and self.current_device_id:
                    if data.get('device_id') == self.current_device_id:
                        print(f"[Calibrate] ✓ 設備ID匹配: {self.current_device_id}")
                        self.calibrate_response = data
                        self.calibrate_received.set()
                    else:
                        print(f"[Calibrate] ⚠ 設備ID不匹配，忽略（期望: {self.current_device_id}, 收到: {data.get('device_id')}）")
                else:
                    self.calibrate_response = data
                    self.calibrate_received.set()
            else:
                print(f"[ShelfConfig] ⚠ 未知主題: {topic}")
        except Exception as e:
            print(f"[ShelfConfig] ✗ 解析訊息失敗: {e}")
            import traceback
            traceback.print_exc()
    
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
        self.current_device_id = device_id  # 記錄當前設備ID，用於訂閱
        
        # 創建 MQTT 客戶端（使用唯一的 Client ID 避免衝突）
        import random
        client_id = f"RPI_ShelfConfig_{random.randint(1000, 9999)}"
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        try:
            # 連接到 MQTT Broker
            print(f"[ShelfConfig] 正在連接到 {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)  # 增加 keepalive 時間
            self.client.loop_start()
            
            # 等待連接建立和訂閱完成
            if not self.connected.wait(5):  # 增加連接超時時間
                print(f"[ShelfConfig] 連接超時")
                return None
            
            print(f"[ShelfConfig] 連接已建立，等待 1 秒確保訂閱完成...")
            time.sleep(1)  # 增加等待時間確保訂閱完成
            
            # ✅ 使用設備特定的配置請求主題
            device_config_request_topic = f"shelf/{device_id}/config/request"
            request = json.dumps({"device_id": device_id})
            result = self.client.publish(device_config_request_topic, request, qos=1)  # 使用 QoS 1
            
            print(f"[ShelfConfig] 發送到主題: {device_config_request_topic}")
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[ShelfConfig] 已發送查詢請求: {request}")
                result.wait_for_publish()  # 等待發送完成
            else:
                print(f"[ShelfConfig] 發送請求失敗，錯誤碼: {result.rc}")
                return None
            
            # 等待回應
            print(f"[ShelfConfig] 等待設備回應（超時 {timeout} 秒）...")
            if self.response_received.wait(timeout):
                print(f"[ShelfConfig] 成功獲取貨架配置")
                time.sleep(0.2)  # 稍微延遲以確保數據完整
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
                time.sleep(0.3)  # 延遲以確保所有處理完成
                self.client.loop_stop()
                time.sleep(0.1)
                self.client.disconnect()
                print(f"[ShelfConfig] 已斷開 MQTT 連接")
    
    def calibrate_shelf_internal(self, device_id, shelf_id, timeout=15):
        """
        校正指定貨架（測量空貨架長度）
        
        Args:
            device_id: 設備 ID
            shelf_id: 完整的貨架 ID (格式: device_id_local_shelf_id)
            timeout: 超時時間（秒）
            
        Returns:
            dict: {'success': bool, 'shelf_length': float, 'error': str}
        """
        print(f"\n{'='*60}")
        print(f"[Calibrate] 開始校正貨架")
        print(f"  設備ID: {device_id}")
        print(f"  完整貨架ID: {shelf_id}")
        
        # ✅ 解析 shelf_id，提取本地貨架 ID
        from database import parse_shelf_id
        parsed_device_id, local_shelf_id = parse_shelf_id(shelf_id)
        
        print(f"  本地貨架ID: {local_shelf_id}")
        print(f"{'='*60}\n")
        
        # 重置回應
        self.calibrate_response = None
        self.calibrate_received.clear()
        self.connected.clear()
        self.current_device_id = device_id  # 記錄當前設備ID
        
        # 創建 MQTT 客戶端（使用唯一的 Client ID 避免衝突）
        import random
        client_id = f"RPI_Calibrate_{random.randint(1000, 9999)}"
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
        try:
            # 連接到 MQTT Broker
            print(f"[Calibrate] 正在連接到 {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)  # 增加 keepalive
            self.client.loop_start()
            
            # 等待連接建立
            if not self.connected.wait(5):  # 增加超時時間
                return {'success': False, 'error': '連接 MQTT 超時'}
            
            time.sleep(1)  # 確保訂閱完成
            
            # ✅ 使用設備特定的命令主題和本地貨架ID
            from config import get_device_command_topic
            device_command_topic = get_device_command_topic(device_id)
            command = f"calibrate {local_shelf_id}"  # 使用本地ID (如 A1)
            
            print(f"[Calibrate] 發送校正命令")
            print(f"  MQTT主題: {device_command_topic}")
            print(f"  命令內容: {command}")
            
            result = self.client.publish(device_command_topic, command, qos=1)  # 使用 QoS 1
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"[Calibrate] 已發送校正命令: {command}")
                result.wait_for_publish()  # 等待發送完成
            else:
                return {'success': False, 'error': f'發送命令失敗，錯誤碼: {result.rc}'}
            
            # 等待校正結果
            print(f"[Calibrate] 等待校正完成（超時 {timeout} 秒）...")
            if self.calibrate_received.wait(timeout):
                if self.calibrate_response:
                    if self.calibrate_response.get('success'):
                        length = self.calibrate_response.get('shelf_length', 0.0)
                        print(f"[Calibrate] 校正成功！長度: {length:.2f} cm")
                        
                        # ✅ 更新資料庫（使用完整的 shelf_id）
                        from database import update_shelf_calibration
                        update_shelf_calibration(shelf_id, length)  # shelf_id已經是完整ID
                        
                        time.sleep(0.2)  # 確保數據完整
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
                time.sleep(0.3)  # 延遲以確保所有處理完成
                self.client.loop_stop()
                time.sleep(0.1)
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

