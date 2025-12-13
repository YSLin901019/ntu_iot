#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT 設備探測模塊
用於發現和列出所有在線的 ESP32S3 設備
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE,
    TOPIC_DISCOVERY, TOPIC_DISCOVERY_RESPONSE,
    DISCOVERY_TIMEOUT
)

class DeviceDiscovery:
    """設備探測類"""
    
    def __init__(self):
        self.discovered_devices = []
        self.discovery_lock = threading.Lock()
        self.client = None
        self.is_discovering = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連接回調"""
        if rc == 0:
            # 訂閱設備回應主題
            client.subscribe(TOPIC_DISCOVERY_RESPONSE)
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息回調 - 接收設備回應"""
        if msg.topic == TOPIC_DISCOVERY_RESPONSE:
            try:
                data = json.loads(msg.payload.decode('utf-8'))
                
                with self.discovery_lock:
                    # 檢查是否已存在
                    if not any(d['device_id'] == data.get('device_id') for d in self.discovered_devices):
                        self.discovered_devices.append({
                            'device_id': data.get('device_id'),
                            'device_name': data.get('device_name', data.get('device_id')),
                            'shelves': data.get('shelves', []),
                            'shelf_count': len(data.get('shelves', [])),
                            'wifi_signal': data.get('wifi_signal', 'N/A'),
                            'uptime_ms': data.get('uptime_ms', 0)
                        })
            except json.JSONDecodeError:
                pass
    
    def discover_devices(self, timeout=DISCOVERY_TIMEOUT):
        """
        探測可用設備
        
        參數:
            timeout: 超時時間（秒）
        
        返回:
            list: 發現的設備列表
        """
        self.discovered_devices = []
        self.is_discovering = True
        
        try:
            # 創建 MQTT 客戶端
            self.client = mqtt.Client(client_id="RPI_Discovery")
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            
            # 連接到 MQTT Broker
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            
            # 開始循環處理
            self.client.loop_start()
            
            # 等待連接成功
            time.sleep(0.5)
            
            # 發送探測請求
            discovery_message = json.dumps({
                'command': 'discover',
                'timestamp': int(time.time() * 1000)
            })
            
            self.client.publish(TOPIC_DISCOVERY, discovery_message)
            
            # 等待回應
            time.sleep(timeout)
            
            # 停止循環
            self.client.loop_stop()
            self.client.disconnect()
            
        except Exception as e:
            print(f"設備探測錯誤: {e}")
        finally:
            self.is_discovering = False
        
        return self.discovered_devices.copy()

# 全局設備探測實例
_device_discovery = DeviceDiscovery()

def discover_available_devices(timeout=DISCOVERY_TIMEOUT):
    """
    探測可用設備（外部調用接口）
    
    參數:
        timeout: 超時時間（秒）
    
    返回:
        list: 發現的設備列表，格式：
        [
            {
                'device_id': 'ESP32_001',
                'device_name': 'ESP32 設備 1',
                'shelves': ['A1', 'A2', 'A3'],
                'shelf_count': 3,
                'wifi_signal': -45,
                'uptime_ms': 123456
            },
            ...
        ]
    """
    return _device_discovery.discover_devices(timeout)

