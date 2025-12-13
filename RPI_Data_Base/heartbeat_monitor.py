#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設備心跳檢測模塊
定期檢查設備是否在線，並更新最後上線時間
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
import sqlite3
from datetime import datetime
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE,
    TOPIC_HEARTBEAT, TOPIC_HEARTBEAT_RESPONSE,
    HEARTBEAT_TIMEOUT, DB_FILE
)

class HeartbeatMonitor:
    """心跳檢測監控器"""
    
    def __init__(self):
        self.client = None
        self.heartbeat_responses = {}
        self.response_lock = threading.Lock()
        self.is_checking = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連接回調"""
        if rc == 0:
            # 訂閱心跳回應主題
            client.subscribe(TOPIC_HEARTBEAT_RESPONSE)
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息回調 - 接收心跳回應"""
        if msg.topic == TOPIC_HEARTBEAT_RESPONSE:
            try:
                data = json.loads(msg.payload.decode('utf-8'))
                device_id = data.get('device_id')
                
                if device_id:
                    with self.response_lock:
                        self.heartbeat_responses[device_id] = {
                            'status': data.get('status', 'online'),
                            'timestamp': data.get('timestamp', 0),
                            'received_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
            except json.JSONDecodeError:
                pass
    
    def check_device(self, device_id, timeout=HEARTBEAT_TIMEOUT):
        """
        檢查單個設備是否在線
        
        參數:
            device_id: 設備 ID
            timeout: 超時時間（秒）
        
        返回:
            dict: {'online': bool, 'timestamp': str} 或 None
        """
        # 清除之前的回應
        with self.response_lock:
            self.heartbeat_responses.pop(device_id, None)
        
        try:
            # 創建 MQTT 客戶端
            self.client = mqtt.Client(client_id=f"RPI_Heartbeat_{int(time.time())}")
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            # 連接到 MQTT Broker
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            
            # 等待連接成功
            time.sleep(0.5)
            
            # 發送心跳請求
            heartbeat_request = json.dumps({
                'target_device': device_id,
                'timestamp': int(time.time() * 1000)
            })
            
            self.client.publish(TOPIC_HEARTBEAT, heartbeat_request)
            
            # 等待回應
            time.sleep(timeout)
            
            # 檢查是否收到回應
            with self.response_lock:
                if device_id in self.heartbeat_responses:
                    result = {
                        'online': True,
                        'timestamp': self.heartbeat_responses[device_id]['received_at']
                    }
                else:
                    result = {
                        'online': False,
                        'timestamp': None
                    }
            
            # 停止循環
            self.client.loop_stop()
            self.client.disconnect()
            
            return result
            
        except Exception as e:
            print(f"心跳檢測錯誤: {e}")
            return None
    
    def check_all_devices(self, timeout=HEARTBEAT_TIMEOUT):
        """
        檢查所有設備是否在線
        
        參數:
            timeout: 超時時間（秒）
        
        返回:
            dict: {device_id: {'online': bool, 'timestamp': str}}
        """
        # 獲取所有設備
        devices = self._get_all_devices()
        
        if not devices:
            return {}
        
        # 清除之前的回應
        with self.response_lock:
            self.heartbeat_responses.clear()
        
        try:
            # 創建 MQTT 客戶端
            self.client = mqtt.Client(client_id=f"RPI_Heartbeat_{int(time.time())}")
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            # 連接到 MQTT Broker
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            
            # 等待連接成功
            time.sleep(0.5)
            
            # 發送廣播心跳請求
            heartbeat_request = json.dumps({
                'type': 'broadcast',
                'timestamp': int(time.time() * 1000)
            })
            
            self.client.publish(TOPIC_HEARTBEAT, heartbeat_request)
            
            # 等待回應
            time.sleep(timeout)
            
            # 更新數據庫中的設備狀態
            results = {}
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for device_id in devices:
                with self.response_lock:
                    if device_id in self.heartbeat_responses:
                        # 設備在線，更新數據庫
                        self._update_device_status(device_id, 'online', current_time)
                        results[device_id] = {
                            'online': True,
                            'timestamp': current_time
                        }
                    else:
                        # 設備離線
                        self._update_device_status(device_id, 'offline', None)
                        results[device_id] = {
                            'online': False,
                            'timestamp': None
                        }
            
            # 停止循環
            self.client.loop_stop()
            self.client.disconnect()
            
            return results
            
        except Exception as e:
            print(f"批量心跳檢測錯誤: {e}")
            return {}
    
    def _get_all_devices(self):
        """獲取所有設備 ID"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT device_id FROM devices')
            devices = [row[0] for row in cursor.fetchall()]
            conn.close()
            return devices
        except Exception:
            return []
    
    def _update_device_status(self, device_id, status, last_seen):
        """更新設備狀態到數據庫"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            if last_seen:
                cursor.execute('''
                    UPDATE devices 
                    SET status = ?, last_seen = ?
                    WHERE device_id = ?
                ''', (status, last_seen, device_id))
            else:
                cursor.execute('''
                    UPDATE devices 
                    SET status = ?
                    WHERE device_id = ?
                ''', (status, device_id))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"更新設備狀態失敗: {e}")

# 全局心跳監控實例
_heartbeat_monitor = HeartbeatMonitor()

def check_device_heartbeat(device_id, timeout=HEARTBEAT_TIMEOUT):
    """
    檢查單個設備心跳（外部調用接口）
    
    參數:
        device_id: 設備 ID
        timeout: 超時時間（秒）
    
    返回:
        dict: {'online': bool, 'timestamp': str}
    """
    return _heartbeat_monitor.check_device(device_id, timeout)

def check_all_devices_heartbeat(timeout=HEARTBEAT_TIMEOUT):
    """
    檢查所有設備心跳（外部調用接口）
    
    參數:
        timeout: 超時時間（秒）
    
    返回:
        dict: {device_id: {'online': bool, 'timestamp': str}}
    """
    return _heartbeat_monitor.check_all_devices(timeout)

