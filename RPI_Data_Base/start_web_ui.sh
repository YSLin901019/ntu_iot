#!/bin/bash
# Web UI 資料庫管理工具啟動腳本

cd "$(dirname "$0")"

echo "======================================================"
echo "Web UI 資料庫管理工具"
echo "======================================================"
echo ""

# 檢查 Flask 是否已安裝
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask 未安裝，正在安裝..."
    pip3 install flask
fi

# 啟動 Web 服務
python3 web_manager.py

