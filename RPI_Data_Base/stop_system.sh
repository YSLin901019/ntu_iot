#!/bin/bash
# ============================================================
# 貨架管理系統 - 停止腳本
# ============================================================

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 工作目錄
WORK_DIR="/home/yslin/iot_final_project/ntu_iot/RPI_Data_Base"
cd "$WORK_DIR"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}        貨架管理系統 - 停止腳本${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# 停止 Web UI
echo -e "${YELLOW}→${NC} 停止 Web UI 服務..."
if pgrep -f "web_manager.py" > /dev/null; then
    pkill -f web_manager.py
    echo -e "${GREEN}  ✓ Web UI 已停止${NC}"
else
    echo -e "  ℹ Web UI 未在運行"
fi

# 停止 MQTT 接收服務
echo -e "\n${YELLOW}→${NC} 停止 MQTT 接收服務..."
if pgrep -f "iot_mqtt.py" > /dev/null; then
    pkill -f iot_mqtt.py
    echo -e "${GREEN}  ✓ MQTT 接收服務已停止${NC}"
else
    echo -e "  ℹ MQTT 接收服務未在運行"
fi

# 清理 port
echo -e "\n${YELLOW}→${NC} 清理佔用的 port..."
if lsof -i :5000 > /dev/null 2>&1; then
    fuser -k 5000/tcp 2>/dev/null || true
    echo -e "${GREEN}  ✓ Port 5000 已釋放${NC}"
fi

# 刪除 PID 文件
rm -f "$WORK_DIR/.mqtt.pid" "$WORK_DIR/.web.pid"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}  ✓ 所有服務已停止${NC}"
echo -e "${GREEN}============================================================${NC}\n"

