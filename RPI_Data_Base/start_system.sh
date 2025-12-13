#!/bin/bash
# ============================================================
# 貨架管理系統 - 自動啟動腳本
# ============================================================

set -e

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
echo -e "${BLUE}        貨架管理系統 - 自動啟動腳本${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# ============================================================
# 步驟 1: 清理所有服務
# ============================================================
echo -e "${YELLOW}[步驟 1/4]${NC} 清理現有服務..."

# 清理 Web UI
if pgrep -f "web_manager.py" > /dev/null; then
    echo -e "  → 停止 Web UI 服務"
    pkill -f web_manager.py
    sleep 1
fi

# 清理 MQTT 接收服務
if pgrep -f "iot_mqtt.py" > /dev/null; then
    echo -e "  → 停止 MQTT 接收服務"
    pkill -f iot_mqtt.py
    sleep 1
fi

# 確認 port 5000 已釋放
if lsof -i :5000 > /dev/null 2>&1; then
    echo -e "  ${YELLOW}→ Port 5000 仍被佔用，強制清理...${NC}"
    fuser -k 5000/tcp 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}  ✓ 服務清理完成${NC}\n"

# ============================================================
# 步驟 2: 檢查 MQTT Broker
# ============================================================
echo -e "${YELLOW}[步驟 2/4]${NC} 檢查 MQTT Broker..."

if systemctl is-active --quiet mosquitto; then
    echo -e "${GREEN}  ✓ Mosquitto 正在運行${NC}\n"
else
    echo -e "${RED}  ✗ Mosquitto 未運行${NC}"
    echo -e "  ${YELLOW}→ 正在啟動 Mosquitto...${NC}"
    sudo systemctl start mosquitto
    sleep 2
    if systemctl is-active --quiet mosquitto; then
        echo -e "${GREEN}  ✓ Mosquitto 已啟動${NC}\n"
    else
        echo -e "${RED}  ✗ Mosquitto 啟動失敗${NC}"
        exit 1
    fi
fi

# ============================================================
# 步驟 3: 啟動 MQTT 接收服務
# ============================================================
echo -e "${YELLOW}[步驟 3/4]${NC} 啟動 MQTT 接收服務..."

nohup python3 iot_mqtt.py > mqtt.log 2>&1 &
MQTT_PID=$!
sleep 2

if ps -p $MQTT_PID > /dev/null; then
    echo -e "${GREEN}  ✓ MQTT 接收服務已啟動 (PID: $MQTT_PID)${NC}"
    echo -e "  → 日誌文件: $WORK_DIR/mqtt.log\n"
else
    echo -e "${RED}  ✗ MQTT 接收服務啟動失敗${NC}"
    echo -e "  → 查看日誌: tail -50 $WORK_DIR/mqtt.log"
    exit 1
fi

# ============================================================
# 步驟 4: 啟動 Web UI 服務
# ============================================================
echo -e "${YELLOW}[步驟 4/4]${NC} 啟動 Web UI 服務..."

nohup python3 web_manager.py > web.log 2>&1 &
WEB_PID=$!
sleep 3

if ps -p $WEB_PID > /dev/null; then
    echo -e "${GREEN}  ✓ Web UI 服務已啟動 (PID: $WEB_PID)${NC}"
    echo -e "  → 日誌文件: $WORK_DIR/web.log"
    
    # 獲取 IP 地址
    IP=$(hostname -I | awk '{print $1}')
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}  🎉 系統啟動成功！${NC}"
    echo -e "${GREEN}============================================================${NC}\n"
    echo -e "  Web UI 訪問地址:"
    echo -e "    → http://localhost:5000"
    echo -e "    → http://${IP}:5000\n"
    echo -e "  服務狀態:"
    echo -e "    → MQTT 接收: PID ${MQTT_PID}"
    echo -e "    → Web UI:    PID ${WEB_PID}\n"
    echo -e "  管理命令:"
    echo -e "    → 查看 MQTT 日誌: tail -f $WORK_DIR/mqtt.log"
    echo -e "    → 查看 Web 日誌:  tail -f $WORK_DIR/web.log"
    echo -e "    → 停止服務:       $WORK_DIR/stop_system.sh"
    echo -e "    → 重啟服務:       $WORK_DIR/start_system.sh\n"
else
    echo -e "${RED}  ✗ Web UI 服務啟動失敗${NC}"
    echo -e "  → 查看日誌: tail -50 $WORK_DIR/web.log"
    exit 1
fi

# 寫入 PID 到文件
echo "$MQTT_PID" > "$WORK_DIR/.mqtt.pid"
echo "$WEB_PID" > "$WORK_DIR/.web.pid"

echo -e "${BLUE}============================================================${NC}\n"

