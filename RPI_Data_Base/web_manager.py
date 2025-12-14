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
    from shelf_control import enable_shelf, disable_shelf
    from database import (
        sync_shelf_config_from_esp32,
        update_shelf_enabled_status,
        get_enabled_shelves,
        get_available_shelves_for_product
    )
    SHELF_CONFIG_ENABLED = True
except ImportError as e:
    SHELF_CONFIG_ENABLED = False
    print(f"警告: 貨架配置模塊未載入 - {e}")

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
        
        # 活躍貨架統計（已啟用的貨架）
        cursor.execute('SELECT COUNT(*) as active FROM shelves WHERE enabled = 1')
        stats['active_shelves'] = cursor.fetchone()['active']
        
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
            
            # 檢查設備是否已存在
            cursor.execute('SELECT device_id FROM devices WHERE device_id = ?', (device_id,))
            existing = cursor.fetchone()
            
            if existing:
                conn.close()
                return render_template('add_device.html', 
                    error=f'設備 {device_id} 已存在，請使用不同的設備 ID 或先刪除舊設備')
            
            # 如果是從探測掃描來的，設為在線狀態
            status = 'online' if from_discovery else 'offline'
            
            cursor.execute('''
                INSERT INTO devices (device_id, device_name, location, status, last_seen)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (device_id, device_name, location, status))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('devices'))
        except sqlite3.IntegrityError as e:
            return render_template('add_device.html', 
                error=f'設備 ID 重複或資料格式錯誤: {str(e)}')
        except Exception as e:
            return render_template('add_device.html', 
                error=f'新增設備失敗: {str(e)}')
    
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
    """刪除設備（級聯刪除關聯資料）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 1. 刪除關聯的感測器數據
        cursor.execute('DELETE FROM sensor_data WHERE device_id = ?', (device_id,))
        
        # 2. 刪除關聯的貨架配置
        cursor.execute('DELETE FROM shelves WHERE device_id = ?', (device_id,))
        
        # 3. 刪除設備本身
        cursor.execute('DELETE FROM devices WHERE device_id = ?', (device_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✓ 已刪除設備 {device_id} 及其所有關聯資料")
        return jsonify({'success': True})
    except Exception as e:
        print(f"✗ 刪除設備失敗: {e}")
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

@app.route('/shelves/<shelf_id>/configure', methods=['GET', 'POST', 'DELETE'])
def configure_shelf_product(shelf_id):
    """配置貨架商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if request.method == 'DELETE':
            # 解除商品綁定
            cursor.execute('''
                UPDATE shelves 
                SET product_id = NULL, 
                    product_name = NULL, 
                    product_length = NULL,
                    stock_quantity = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE shelf_id = ?
            ''', (shelf_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 的商品綁定已解除'
            })
        
        # GET 或 POST 請求
        # 獲取貨架資訊
        cursor.execute('''
            SELECT s.*, d.device_name, d.location
            FROM shelves s
            LEFT JOIN devices d ON s.device_id = d.device_id
            WHERE s.shelf_id = ?
        ''', (shelf_id,))
        
        shelf = cursor.fetchone()
        
        if not shelf:
            conn.close()
            return "找不到貨架", 404
        
        shelf = dict(shelf)
        
        # 檢查貨架是否啟用（雙重保護）
        if not shelf.get('enabled'):
            conn.close()
            return render_template('error.html', 
                                 title='貨架未啟用',
                                 message=f'貨架 {shelf_id} 尚未啟用，無法配置商品。',
                                 action_text='返回貨架管理',
                                 action_url=url_for('shelves')), 403
        
        # 獲取設備資訊
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (shelf['device_id'],))
        device = dict(cursor.fetchone())
        
        if request.method == 'POST':
            # 更新商品綁定
            product_id = request.form.get('product_id')
            stock_quantity = int(request.form.get('stock_quantity', 0))
            
            # 獲取商品資訊
            cursor.execute('SELECT * FROM products WHERE product_id = ?', (product_id,))
            product = cursor.fetchone()
            
            if not product:
                conn.close()
                return "找不到商品", 404
            
            product = dict(product)
            
            # 更新貨架
            cursor.execute('''
                UPDATE shelves 
                SET product_id = ?,
                    product_name = ?,
                    product_length = ?,
                    stock_quantity = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE shelf_id = ?
            ''', (product_id, product['product_name'], product['product_length'], 
                  stock_quantity, shelf_id))
            
            conn.commit()
            conn.close()
            
            return redirect(url_for('shelves'))
        
        # GET 請求 - 顯示配置頁面
        # 獲取所有商品列表
        cursor.execute('SELECT * FROM products ORDER BY product_name')
        products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('configure_shelf.html', 
                             shelf=shelf, 
                             device=device,
                             products=products)
                             
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
    return render_template('sensor_data.html')

# ==================== 路由 - 補貨提醒 ====================
@app.route('/restock_alert')
def restock_alert():
    """補貨提醒頁面"""
    return render_template('restock_alert.html')

@app.route('/api/restock_alert')
def api_restock_alert():
    """API - 獲取需要補貨的貨架"""
    try:
        location = request.args.get('location', '')
        product_name = request.args.get('product_name', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 查詢：貨架已配置商品 + 最新數據為空的狀態
        query = '''
            SELECT 
                s.shelf_id,
                s.device_id,
                s.product_name,
                s.product_length,
                s.shelf_length,
                d.device_name,
                d.location,
                sd.timestamp as last_update,
                sd.distance_cm,
                sd.occupied
            FROM shelves s
            INNER JOIN devices d ON s.device_id = d.device_id
            LEFT JOIN (
                SELECT shelf_id, timestamp, distance_cm, occupied,
                       ROW_NUMBER() OVER (PARTITION BY shelf_id ORDER BY timestamp DESC) as rn
                FROM sensor_data
            ) sd ON s.shelf_id = sd.shelf_id AND sd.rn = 1
            WHERE s.product_name IS NOT NULL 
              AND s.product_name != ""
              AND s.enabled = 1
              AND (sd.occupied = 0 OR sd.occupied IS NULL)
        '''
        
        params = []
        
        if location:
            query += ' AND d.location = ?'
            params.append(location)
        
        if product_name:
            query += ' AND s.product_name = ?'
            params.append(product_name)
        
        query += ' ORDER BY sd.timestamp DESC'
        
        cursor.execute(query, params)
        alerts = [dict(row) for row in cursor.fetchall()]
        
        # 獲取統計資訊
        total_alerts = len(alerts)
        
        # 獲取篩選選項
        cursor.execute('SELECT DISTINCT location FROM devices WHERE location IS NOT NULL AND location != "" ORDER BY location')
        locations = [row['location'] for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT DISTINCT product_name 
            FROM shelves 
            WHERE product_name IS NOT NULL AND product_name != "" 
            ORDER BY product_name
        ''')
        products = [row['product_name'] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'stats': {
                'total_alerts': total_alerts
            },
            'filters': {
                'locations': locations,
                'products': products
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sensor_data/delete', methods=['POST'])
def delete_sensor_data():
    """API - 刪除感測器歷史數據"""
    try:
        from database import delete_sensor_data_by_time, delete_sensor_data_by_device, delete_sensor_data_by_shelf
        
        data = request.get_json()
        delete_type = data.get('type')  # 'time', 'device', 'shelf', 'all'
        
        if delete_type == 'all':
            result = delete_sensor_data_by_time(all_data=True)
        elif delete_type == 'time':
            days = data.get('days')
            hours = data.get('hours')
            result = delete_sensor_data_by_time(days=days, hours=hours)
        elif delete_type == 'device':
            device_id = data.get('device_id')
            result = delete_sensor_data_by_device(device_id)
        elif delete_type == 'shelf':
            shelf_id = data.get('shelf_id')
            result = delete_sensor_data_by_shelf(shelf_id)
        else:
            return jsonify({'success': False, 'error': '無效的刪除類型'}), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sensor_data')
def api_sensor_data():
    """API - 獲取感測器數據（用於 AJAX 更新）"""
    try:
        location = request.args.get('location', '')
        device_id = request.args.get('device_id', '')
        shelf_id = request.args.get('shelf_id', '')
        product_name = request.args.get('product_name', '')
        limit = int(request.args.get('limit', 50))
        occupied = request.args.get('occupied', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # 構建查詢 - 包含設備區域資訊
        query = '''
            SELECT sd.*, s.product_name, d.location as device_location
            FROM sensor_data sd
            LEFT JOIN shelves s ON sd.shelf_id = s.shelf_id
            LEFT JOIN devices d ON sd.device_id = d.device_id
            WHERE 1=1
        '''
        params = []
        
        if location:
            query += ' AND d.location = ?'
            params.append(location)
        
        if device_id:
            query += ' AND sd.device_id = ?'
            params.append(device_id)
        
        if shelf_id:
            query += ' AND sd.shelf_id = ?'
            params.append(shelf_id)
        
        if product_name:
            query += ' AND s.product_name = ?'
            params.append(product_name)
        
        if occupied:
            query += ' AND sd.occupied = ?'
            params.append(int(occupied))
        
        query += ' ORDER BY sd.timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        
        # 獲取統計資訊
        cursor.execute('SELECT COUNT(*) as count FROM sensor_data')
        total_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(DISTINCT device_id) as count FROM sensor_data')
        device_count = cursor.fetchone()['count']
        
        # 活躍貨架：已啟用的貨架數量
        cursor.execute('SELECT COUNT(*) as count FROM shelves WHERE enabled = 1')
        shelf_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT MAX(timestamp) as last_update FROM sensor_data')
        last_update_row = cursor.fetchone()
        last_update = last_update_row['last_update'] if last_update_row else None
        
        # 獲取篩選選項
        cursor.execute('SELECT DISTINCT device_id FROM sensor_data ORDER BY device_id')
        devices = [row['device_id'] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT shelf_id FROM sensor_data ORDER BY shelf_id')
        shelves = [row['shelf_id'] for row in cursor.fetchall()]
        
        # 獲取所有不重複的區域（從 devices 表）
        cursor.execute('SELECT DISTINCT location FROM devices WHERE location IS NOT NULL AND location != "" ORDER BY location')
        locations = [row['location'] for row in cursor.fetchall()]
        
        # 獲取所有不重複的商品名稱（從 shelves 表）
        cursor.execute('SELECT DISTINCT product_name FROM shelves WHERE product_name IS NOT NULL AND product_name != "" ORDER BY product_name')
        products = [row['product_name'] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': {
                'total_count': total_count,
                'device_count': device_count,
                'shelf_count': shelf_count,
                'last_update': last_update
            },
            'filters': {
                'devices': devices,
                'shelves': shelves,
                'locations': locations,
                'products': products
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        # 1. 從數據庫獲取貨架所屬的設備 ID
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT device_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'success': False,
                'error': f'找不到貨架 {shelf_id}'
            }), 404
        
        device_id = result['device_id']
        
        # 2. 更新數據庫
        db_success = update_shelf_enabled_status(shelf_id, True)
        
        if not db_success:
            return jsonify({
                'success': False,
                'error': f'更新數據庫失敗'
            }), 400
        
        # 3. 向 ESP32S3 發送啟用命令
        mqtt_success = enable_shelf(device_id, shelf_id)
        
        if mqtt_success:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 已啟用',
                'synced': True
            })
        else:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 數據庫已更新，但 MQTT 命令發送失敗',
                'synced': False
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shelves/<shelf_id>/calibrate', methods=['POST'])
def api_calibrate_shelf(shelf_id):
    """API - 校正貨架（測量空貨架長度）"""
    if not SHELF_CONFIG_ENABLED:
        return jsonify({
            'success': False,
            'error': '貨架配置模塊未啟用'
        }), 500
    
    try:
        # 1. 獲取請求數據
        data = request.get_json() or {}
        device_id = data.get('device_id')
        
        if not device_id:
            # 從數據庫獲取設備 ID
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT device_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return jsonify({
                    'success': False,
                    'error': f'找不到貨架 {shelf_id}'
                }), 404
            
            device_id = result['device_id']
        
        # 2. 發送校正命令到 ESP32
        from shelf_config_manager import calibrate_shelf
        result = calibrate_shelf(device_id, shelf_id, timeout=15)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 校正成功',
                'shelf_length': result['shelf_length']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '校正失敗')
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
        # 1. 從數據庫獲取貨架所屬的設備 ID
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT device_id FROM shelves WHERE shelf_id = ?', (shelf_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'success': False,
                'error': f'找不到貨架 {shelf_id}'
            }), 404
        
        device_id = result['device_id']
        
        # 2. 更新數據庫
        db_success = update_shelf_enabled_status(shelf_id, False)
        
        if not db_success:
            return jsonify({
                'success': False,
                'error': f'更新數據庫失敗'
            }), 400
        
        # 3. 向 ESP32S3 發送停用命令
        mqtt_success = disable_shelf(device_id, shelf_id)
        
        if mqtt_success:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 已停用',
                'synced': True
            })
        else:
            return jsonify({
                'success': True,
                'message': f'貨架 {shelf_id} 數據庫已更新，但 MQTT 命令發送失敗',
                'synced': False
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shelves/<shelf_id>/product')
def api_get_shelf_product(shelf_id):
    """API - 獲取貨架配置的商品資訊"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT product_name, product_length, stock_quantity
            FROM shelves
            WHERE shelf_id = ?
        ''', (shelf_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result['product_name']:
            return jsonify({
                'success': True,
                'product': {
                    'product_name': result['product_name'],
                    'product_length': result['product_length'],
                    'stock_quantity': result['stock_quantity']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '尚未配置商品'
            })
            
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

