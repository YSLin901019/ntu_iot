#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試貨架配置查詢
"""

import sys
import time
from shelf_config_manager import query_device_shelf_config

if len(sys.argv) < 2:
    print("使用方法: python3 test_shelf_config.py <device_id>")
    print("例如: python3 test_shelf_config.py ESP32S3_3878929E139C")
    sys.exit(1)

device_id = sys.argv[1]

print("=" * 60)
print(f"測試貨架配置查詢: {device_id}")
print("=" * 60)

config = query_device_shelf_config(device_id, timeout=10)

print("\n" + "=" * 60)
if config:
    print("✅ 查詢成功!")
    print("=" * 60)
    print(f"\n設備 ID: {config['device_id']}")
    print(f"貨架總數: {config['total_count']}")
    print(f"已啟用數: {config['enabled_count']}")
    print("\n貨架列表:")
    print("-" * 60)
    for shelf in config['shelves']:
        status = "✅ 已啟用" if shelf['enabled'] else "❌ 停用"
        print(f"  [{shelf['shelf_id']}] GPIO:{shelf['gpio']:2d} Index:{shelf['index']:2d} - {status}")
    print("=" * 60)
else:
    print("❌ 查詢失敗")
    print("=" * 60)
    print("\n可能的原因:")
    print("1. 設備離線")
    print("2. 設備 ID 不正確")
    print("3. MQTT Broker 未運行")
    print("4. 網絡連接問題")
    sys.exit(1)

