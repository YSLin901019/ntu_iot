#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
貨架控制模塊
向 ESP32S3 發送啟用/停用命令
支援多設備架構 - 使用設備特定MQTT主題
"""

import paho.mqtt.client as mqtt
import time
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE,
    TOPIC_COMMAND,
    get_device_command_topic
)
from database import parse_shelf_id

def send_shelf_command(device_id: str, shelf_id: str, enable: bool) -> bool:
    """
    向指定設備發送貨架啟用/停用命令
    
    Args:
        device_id: 設備 ID
        shelf_id: 完整的貨架 ID (格式: device_id_local_shelf_id)
        enable: True 為啟用，False 為停用
        
    Returns:
        bool: 發送成功返回 True，失敗返回 False
    """
    # ✅ 解析 shelf_id，提取本地貨架 ID
    parsed_device_id, local_shelf_id = parse_shelf_id(shelf_id)
    
    # 驗證設備ID是否一致
    if parsed_device_id and parsed_device_id != device_id:
        print(f"[ShelfControl] ⚠ 警告: shelf_id 中的設備ID ({parsed_device_id}) 與傳入的 device_id ({device_id}) 不一致")
    
    # ESP32 端只需要本地貨架 ID (如 A1, B2)
    command = f"enable {local_shelf_id}" if enable else f"disable {local_shelf_id}"
    action = "啟用" if enable else "停用"
    
    # ✅ 使用設備特定的命令主題
    device_topic = get_device_command_topic(device_id)
    
    print(f"\n{'='*60}")
    print(f"[ShelfControl] 發送貨架{action}命令")
    print(f"  目標設備: {device_id}")
    print(f"  完整貨架ID: {shelf_id}")
    print(f"  本地貨架ID: {local_shelf_id}")
    print(f"  MQTT主題: {device_topic}")
    print(f"  命令內容: {command}")
    print(f"{'='*60}")
    
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        
        # 等待連接建立
        time.sleep(0.5)
        
        # ✅ 發送命令到設備特定主題
        result = client.publish(device_topic, command, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[ShelfControl] ✓ 已發送{action}命令: {shelf_id}")
            success = True
        else:
            print(f"[ShelfControl] ✗ 發送命令失敗，錯誤碼: {result.rc}")
            success = False
        
        client.loop_stop()
        client.disconnect()
        
        return success
        
    except Exception as e:
        print(f"[ShelfControl] ✗ 發送命令時發生錯誤: {e}")
        return False


def enable_shelf(device_id: str, shelf_id: str) -> bool:
    """啟用貨架"""
    return send_shelf_command(device_id, shelf_id, True)


def disable_shelf(device_id: str, shelf_id: str) -> bool:
    """停用貨架"""
    return send_shelf_command(device_id, shelf_id, False)


if __name__ == "__main__":
    # 測試
    import sys
    
    if len(sys.argv) < 4:
        print("使用方法:")
        print("  啟用: python3 shelf_control.py <device_id> <shelf_id> enable")
        print("  停用: python3 shelf_control.py <device_id> <shelf_id> disable")
        print("\n例如:")
        print("  python3 shelf_control.py ESP32S3_3878929E139C A1 enable")
        print("  python3 shelf_control.py ESP32S3_3878929E139C A1 disable")
        sys.exit(1)
    
    device_id = sys.argv[1]
    shelf_id = sys.argv[2]
    action = sys.argv[3].lower()
    
    if action == "enable":
        success = enable_shelf(device_id, shelf_id)
    elif action == "disable":
        success = disable_shelf(device_id, shelf_id)
    else:
        print(f"未知操作: {action}")
        print("請使用 'enable' 或 'disable'")
        sys.exit(1)
    
    if success:
        print(f"\n✅ 命令發送成功")
    else:
        print(f"\n❌ 命令發送失敗")
        sys.exit(1)

