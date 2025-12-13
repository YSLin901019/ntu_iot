#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web UI 資料庫管理工具
使用 Flask 提供 Web 界面來管理設備、貨架、商品和查詢數據
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from datetime import datetime
import os
import sys

# 添加設備探測模塊
try:
    from device_discovery import discover_available_devices
    DISCOVERY_ENABLED = True
except ImportError:
    DISCOVERY_ENABLED = False
    print("警告: 設備探測模塊未載入")

# 添加心跳檢測模塊
try:
    from heartbeat_monitor import check_device_heartbeat, check_all_devices_heartbeat
    HEARTBEAT_ENABLED = True
except ImportError:
    HEARTBEAT_ENABLED = False
    print("警告: 心跳檢測模塊未載入")

# 添加貨架配置管理模塊
try:
    from shelf_config_manager import query_device_shelf_config
    from database import (
        sync_shelf_config_from_esp32,
        update_shelf_enabled_status,
        get_enabled_shelves,
        get_available_shelves_for_product
    )
    SHELF_CONFIG_ENABLED = True
except ImportError:
    SHELF_CONFIG_ENABLED = False
    print("警告: 貨架配置模塊未載入")

app = Flask(__name__)
DB_FILE = "shelf_data.db"

# ==================== 數據庫輔助函數 ====================
def get_db():
    """獲取數據庫連接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 路由 - 主頁 ====================
@app.route('/')
def index():
    """主頁 - 顯示系統統計"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 獲取統計數據
        stats = {}
        
        # 設備統計
        cursor.execute('SELECT COUNT(*) as total FROM devices')
        stats['device_count'] = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as online FROM devices WHERE status = 'online'")
        stats['online_devices'] = cursor.fetchone()['online']
        
        # 貨架統計
        cursor.execute('SELECT COUNT(*) as total FROM shelves')
        stats['shelf_count'] = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as with_product FROM shelves WHERE product_id IS NOT NULL')
        stats['shelves_with_products'] = cursor.fetchone()['with_product']
        
        # 商品統計
        cursor.execute('SELECT COUNT(*) as total FROM products')
        stats['product_count'] = cursor.fetchone()['total']
        
        cursor.execute('SELECT SUM(stock_quantity) as total_stock FROM shelves')
        result = cursor.fetchone()
        stats['total_stock'] = result['total_stock'] or 0
        
        # 數據統計
        cursor.execute('SELECT COUNT(*) as total FROM sensor_data')
        stats['data_count'] = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as occupied FROM sensor_data WHERE occupied = 1')
        stats['occupied_count'] = cursor.fetchone()['occupied']
        
        if stats['data_count'] > 0:
            stats['occupancy_rate'] = (stats['occupied_count'] / stats['data_count']) * 100
        else:
            stats['occupancy_rate'] = 0
        
        conn.close()
        
        return render_template('index.html', stats=stats)
    except Exception as e:
        return f"錯誤: {e}", 500

# ==================== 路由 - 設備管理 ====================
@app.route('/devices')
def devices():
    """設備列表頁面"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT d.*, COUNT(s.shelf_id) as shelf_count
            FROM devices d
            LEFT JOIN shelves s ON d.device_id = s.device_id
            GROUP BY d.device_id
            ORDER BY d.device_id
        ''')
        
        devices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return render_template('devices.html', devices=devices)
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/devices/add', methods=['GET', 'POST'])
def add_device():
    """新增設備"""
    if request.method == 'POST':
        try:
            device_id = request.form['device_id']
            device_name = request.form['device_name']
            location = request.form.get('location', '')
            from_discovery = request.form.get('from_discovery', 'false') == 'true'
            
            conn = get_db()
            cursor = conn.cursor()
            
            # 如果是從探測掃描來的，設為在線狀態
            status = 'online' if from_discovery else 'offline'
            
            cursor.execute('''
                INSERT INTO devices (device_id, device_name, location, status, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (device_id, device_name, location, status))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('devices'))
        except sqlite3.IntegrityError:
            return "設備 ID 已存在", 400
        except Exception as e:
            return f"錯誤: {e}", 500
    
    return render_template('add_device.html')

@app.route('/devices/<device_id>/edit', methods=['GET', 'POST'])
def edit_device(device_id):
    """編輯設備 - 指定負責區域"""
    if request.method == 'POST':
        try:
            device_name = request.form['device_name']
            location = request.form.get('location', '')
            
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE devices 
                SET device_name = ?, location = ?
                WHERE device_id = ?
            ''', (device_name, location, device_id))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('devices'))
        except Exception as e:
            return f"錯誤: {e}", 500
    
    # GET - 顯示編輯表單
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        device = cursor.fetchone()
        
        if not device:
            return "找不到設備", 404
        
        conn.close()
        
        return render_template('edit_device.html', device=dict(device))
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """刪除設備"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 路由 - 商品管理 ====================
@app.route('/products')
def products():
    """商品列表頁面"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 聯接 shelves 和 devices 表來獲取商品位置資訊
        cursor.execute('''
            SELECT p.*, 
                   s.shelf_id, 
                   s.stock_quantity,
                   d.location as area_location,
                   d.device_name
            FROM products p
            LEFT JOIN shelves s ON p.product_id = s.product_id
            LEFT JOIN devices d ON s.device_id = d.device_id
            ORDER BY p.product_id
        ''')
        
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return render_template('products.html', products=products)
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    """新增商品"""
    if request.method == 'POST':
        try:
            product_id = request.form['product_id']
            product_name = request.form['product_name']
            product_length = float(request.form['product_length'])
            description = request.form.get('description', '')
            shelf_id = request.form.get('shelf_id')  # 選擇的貨架
            stock_quantity = int(request.form.get('stock_quantity', 0))
            
            conn = get_db()
            cursor = conn.cursor()
            
            # 1. 新增商品到 products 表
            cursor.execute('''
                INSERT INTO products (product_id, product_name, product_length, description)
                VALUES (?, ?, ?, ?)
            ''', (product_id, product_name, product_length, description or None))
            
            # 2. 如果選擇了貨架，則將商品綁定到貨架
            if shelf_id:
                cursor.execute('''
                    UPDATE shelves 
                    SET product_id = ?, 
                        product_name = ?, 
                        product_length = ?,
                        stock_quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE shelf_id = ?
                ''', (product_id, product_name, product_length, stock_quantity, shelf_id))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('products'))
        except sqlite3.IntegrityError:
            return "商品 ID 已存在", 400
        except Exception as e:
            return f"錯誤: {e}", 500
    
    # GET - 顯示表單，獲取區域列表
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 獲取所有已配置區域的設備
        cursor.execute('''
            SELECT DISTINCT location 
            FROM devices 
            WHERE location IS NOT NULL AND location != ''
            ORDER BY location
        ''')
        locations = [row['location'] for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('add_product.html', locations=locations)
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/api/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """刪除商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE product_id = ?', (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 路由 - 貨架管理 ====================
@app.route('/shelves')
def shelves():
    """貨架列表頁面 - 按設備分組顯示"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 獲取所有設備
        cursor.execute('''
            SELECT device_id, device_name, location, status
            FROM devices
            ORDER BY device_name, device_id
        ''')
        
        devices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return render_template('shelves.html', devices=devices)
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/shelves/add', methods=['GET', 'POST'])
def add_shelf():
    """新增貨架"""
    if request.method == 'POST':
        try:
            shelf_id = request.form['shelf_id']
            device_id = request.form['device_id']
            max_distance = float(request.form['max_distance'])
            product_id = request.form.get('product_id') or None
            stock_quantity = int(request.form.get('stock_quantity', 0))
            position_index = int(request.form.get('position_index', 0))
            
            # 獲取商品資訊
            product_name = None
            product_length = None
            if product_id:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT product_name, product_length FROM products WHERE product_id = ?', (product_id,))
                result = cursor.fetchone()
                if result:
                    product_name = result['product_name']
                    product_length = result['product_length']
                conn.close()
            
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO shelves 
                (shelf_id, device_id, product_id, product_name, product_length, 
                 max_distance, stock_quantity, position_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (shelf_id, device_id, product_id, product_name, product_length, 
                  max_distance, stock_quantity, position_index))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('shelves'))
        except sqlite3.IntegrityError:
            return "貨架 ID 已存在", 400
        except Exception as e:
            return f"錯誤: {e}", 500
    
    # GET - 顯示表單
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT device_id, device_name FROM devices ORDER BY device_id')
        devices = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT product_id, product_name FROM products ORDER BY product_id')
        products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('add_shelf.html', devices=devices, products=products)
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/shelves/<shelf_id>/update_stock', methods=['POST'])
def update_stock(shelf_id):
    """更新庫存"""
    try:
        new_quantity = int(request.form['stock_quantity'])
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 獲取當前庫存
        cursor.execute('SELECT stock_quantity, product_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        
        if not result:
            return "找不到貨架", 404
        
        old_quantity = result['stock_quantity']
        product_id = result['product_id']
        
        # 更新庫存
        cursor.execute('''
            UPDATE shelves 
            SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE shelf_id = ?
        ''', (new_quantity, shelf_id))
        
        # 記錄變化
        if product_id:
            cursor.execute('''
                INSERT INTO stock_changes 
                (shelf_id, product_id, change_type, quantity_before, quantity_after)
                VALUES (?, ?, 'manual', ?, ?)
            ''', (shelf_id, product_id, old_quantity, new_quantity))
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('shelves'))
    except Exception as e:
        return f"錯誤: {e}", 500

@app.route('/api/shelves/<shelf_id>', methods=['DELETE'])
def delete_shelf(shelf_id):
    """刪除貨架"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM shelves WHERE shelf_id = ?', (shelf_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== 路由 - 感測器數據 ====================
@app.route('/sensor_data')
def sensor_data():
    """感測器數據頁面"""
    try:
        device_id = request.args.get('device_id')
        shelf_id = request.args.get('shelf_id')
        limit = int(request.args.get('limit', 50))
        
        conn = get_db()
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM sensor_data
            WHERE 1=1
        '''
        params = []
        
        if device_id:
            query += ' AND device_id = ?'
            params.append(device_id)
        
        if shelf_id:
            query += ' AND shelf_id = ?'
            params.append(shelf_id)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        
        # 獲取設備列表用於篩選
        cursor.execute('SELECT DISTINCT device_id FROM sensor_data ORDER BY device_id')
        devices = [row['device_id'] for row in cursor.fetchall()]
        
        # 獲取貨架列表用於篩選
        cursor.execute('SELECT DISTINCT shelf_id FROM sensor_data ORDER BY shelf_id')
        shelves = [row['shelf_id'] for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('sensor_data.html', 
                             data=data, 
                             devices=devices, 
                             shelves_list=shelves,
                             current_device=device_id,
                             current_shelf=shelf_id,
                             limit=limit)
    except Exception as e:
        return f"錯誤: {e}", 500

# ==================== API 路由 ====================
@app.route('/api/stats')
def api_stats():
    """API - 獲取統計數據"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) as count FROM devices')
        stats['devices'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM shelves')
        stats['shelves'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM products')
        stats['products'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM sensor_data')
        stats['sensor_records'] = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/unassigned')
def api_unassigned_devices():
    """API - 獲取未分配區域的設備列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT device_id, device_name, status, last_seen
            FROM devices 
            WHERE location IS NULL OR location = ''
            ORDER BY last_seen DESC
        ''')
        
        devices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'count': len(devices),
            'devices': devices
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shelves/by-location/<location>')
def api_shelves_by_location(location):
    """API - 根據區域獲取可用貨架列表（只返回啟用且未綁定商品的貨架）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 獲取該區域下所有啟用且未綁定商品的貨架
        cursor.execute('''
            SELECT s.shelf_id, s.device_id, s.max_distance, s.position_index, s.gpio, s.enabled, d.device_name
            FROM shelves s
            JOIN devices d ON s.device_id = d.device_id
            WHERE d.location = ? 
              AND (s.product_id IS NULL OR s.product_id = '')
              AND s.enabled = 1
            ORDER BY s.position_index, s.shelf_id
        ''', (location,))
        
        shelves = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'count': len(shelves),
            'shelves': shelves
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devices/discover')
def api_discover_devices():
    """API - 探測可用的 ESP32S3 設備"""
    if not DISCOVERY_ENABLED:
        return jsonify({
            'success': False,
            'error': '設備探測模塊未啟用'
        }), 500
    
    try:
        # 執行設備探測
        devices = discover_available_devices(timeout=5)
        
        return jsonify({
            'success': True,
            'count': len(devices),
            'devices': devices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/<device_id>/heartbeat')
def api_device_heartbeat(device_id):
    """API - 檢查單個設備心跳"""
    if not HEARTBEAT_ENABLED:
        return jsonify({
            'success': False,
            'error': '心跳檢測模塊未啟用'
        }), 500
    
    try:
        result = check_device_heartbeat(device_id, timeout=5)
        
        if result:
            return jsonify({
                'success': True,
                'device_id': device_id,
                'online': result['online'],
                'last_seen': result['timestamp']
            })
        else:
            return jsonify({
                'success': False,
                'error': '心跳檢測失敗'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/devices/heartbeat/all')
def api_all_devices_heartbeat():
    """API - 檢查所有設備心跳"""
    if not HEARTBEAT_ENABLED:
        return jsonify({
            'success': False,
            'error': '心跳檢測模塊未啟用'
        }), 500
    
    try:
        results = check_all_devices_heartbeat(timeout=5)
        
        return jsonify({
            'success': True,
            'devices': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== API - 貨架配置管理 ====================
@app.route('/api/shelves/config/<device_id>')
def api_get_shelf_config(device_id):
    """API - 查詢設備的貨架配置（從 ESP32S3）"""
    if not SHELF_CONFIG_ENABLED:
        return jsonify({
            'success': False,
            'error': '貨架配置模塊未啟用'
        }), 500
    
    try:
        config = query_device_shelf_config(device_id, timeout=5)
        
        if config:
            # 同步到數據庫
            sync_shelf_config_from_esp32(device_id, config['shelves'])
            
            return jsonify({
                'success': True,
                'config': config
            })
        else:
            return jsonify({
                'success': False,
                'error': '無法獲取貨架配置，設備可能離線'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shelves/<shelf_id>/enable', methods=['POST'])
def api_enable_shelf(shelf_id):
    """API - 啟用貨架"""
    if not SHELF_CONFIG_ENABLED:
        return jsonify({
            'success': False,
            'error': '貨架配置模塊未啟用'
        }), 500
    
    try:
        success = update_shelf_enabled_status(shelf_id, True)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 已啟用'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'啟用貨架 {shelf_id} 失敗'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shelves/<shelf_id>/disable', methods=['POST'])
def api_disable_shelf(shelf_id):
    """API - 停用貨架"""
    if not SHELF_CONFIG_ENABLED:
        return jsonify({
            'success': False,
            'error': '貨架配置模塊未啟用'
        }), 500
    
    try:
        success = update_shelf_enabled_status(shelf_id, False)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 已停用'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'停用貨架 {shelf_id} 失敗'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shelves/available/<location>')
def api_get_available_shelves(location):
    """API - 獲取指定區域的可用貨架（已啟用且未綁定商品）"""
    if not SHELF_CONFIG_ENABLED:
        return jsonify({
            'success': False,
            'error': '貨架配置模塊未啟用'
        }), 500
    
    try:
        shelves = get_available_shelves_for_product(location)
        
        return jsonify({
            'success': True,
            'shelves': shelves
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 啟動應用 ====================
if __name__ == '__main__':
    # 檢查資料庫是否存在
    if not os.path.exists(DB_FILE):
        print(f"警告: 找不到資料庫文件 {DB_FILE}")
        print("請先執行 iot_mqtt.py 初始化資料庫")
    
    print("=" * 60)
    print("Web UI 資料庫管理工具")
    print("=" * 60)
    print(f"資料庫: {DB_FILE}")
    print("啟動中...")
    print("\n訪問 http://localhost:5000 來使用管理介面")
    print("按 Ctrl+C 停止服務")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

