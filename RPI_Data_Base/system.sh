#!/bin/bash
# ============================================================
# 貨架管理系統 - 統一啟動與管理腳本
# 使用方法: ./system.sh
# 按 Ctrl+C 可優雅地關閉所有服務
# ============================================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 工作目錄
WORK_DIR="/home/yslin/iot_final_project/ntu_iot/RPI_Data_Base"
cd "$WORK_DIR"

# PID 變數
MQTT_PID=""
WEB_PID=""

# ============================================================
# 清理函數 - 在退出時調用
# ============================================================
cleanup() {
    echo -e "\n\n${YELLOW}============================================================${NC}"
    echo -e "${YELLOW}  收到終止信號，正在關閉系統...${NC}"
    echo -e "${YELLOW}============================================================${NC}\n"
    
    # 停止 Web UI
    echo -e "${CYAN}→${NC} 停止 Web UI 服務..."
    if [ -n "$WEB_PID" ] && ps -p $WEB_PID > /dev/null 2>&1; then
        kill $WEB_PID 2>/dev/null || true
        echo -e "${GREEN}  ✓ Web UI 已停止 (PID: $WEB_PID)${NC}"
    fi
    if pgrep -f "web_manager.py" > /dev/null; then
        pkill -f web_manager.py
        echo -e "${GREEN}  ✓ 清理殘留的 Web UI 進程${NC}"
    fi
    
    # 停止 MQTT 接收服務
    echo -e "\n${CYAN}→${NC} 停止 MQTT 接收服務..."
    if [ -n "$MQTT_PID" ] && ps -p $MQTT_PID > /dev/null 2>&1; then
        kill $MQTT_PID 2>/dev/null || true
        echo -e "${GREEN}  ✓ MQTT 接收服務已停止 (PID: $MQTT_PID)${NC}"
    fi
    if pgrep -f "iot_mqtt.py" > /dev/null; then
        pkill -f iot_mqtt.py
        echo -e "${GREEN}  ✓ 清理殘留的 MQTT 進程${NC}"
    fi
    
    # 清理 port
    echo -e "\n${CYAN}→${NC} 清理佔用的 port..."
    if lsof -i :5000 > /dev/null 2>&1; then
        fuser -k 5000/tcp 2>/dev/null || true
        echo -e "${GREEN}  ✓ Port 5000 已釋放${NC}"
    else
        echo -e "  ℹ  Port 5000 未被佔用"
    fi
    
    # 刪除 PID 文件
    rm -f "$WORK_DIR/.mqtt.pid" "$WORK_DIR/.web.pid"
    
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}  ✓ 所有服務已關閉，系統已清理${NC}"
    echo -e "${GREEN}============================================================${NC}\n"
    
    exit 0
}

# 註冊信號處理器 - 捕獲 Ctrl+C (SIGINT) 和 SIGTERM
trap cleanup SIGINT SIGTERM

# ============================================================
# 主程序開始
# ============================================================
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}        貨架管理系統 - 統一啟動腳本${NC}"
echo -e "${BLUE}============================================================${NC}\n"
echo -e "${CYAN}提示: 按 Ctrl+C 可優雅地關閉所有服務${NC}\n"

# ============================================================
# 步驟 1: 清理現有服務
# ============================================================
echo -e "${YELLOW}[步驟 1/4]${NC} 清理現有服務..."

# 清理 Web UI
if pgrep -f "web_manager.py" > /dev/null; then
    echo -e "  → 停止現有的 Web UI 服務"
    pkill -f web_manager.py
    sleep 1
fi

# 清理 MQTT 接收服務
if pgrep -f "iot_mqtt.py" > /dev/null; then
    echo -e "  → 停止現有的 MQTT 接收服務"
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

python3 iot_mqtt.py > mqtt.log 2>&1 &
MQTT_PID=$!
sleep 2

if ps -p $MQTT_PID > /dev/null; then
    echo -e "${GREEN}  ✓ MQTT 接收服務已啟動 (PID: $MQTT_PID)${NC}"
    echo -e "  → 日誌文件: $WORK_DIR/mqtt.log\n"
    echo "$MQTT_PID" > "$WORK_DIR/.mqtt.pid"
else
    echo -e "${RED}  ✗ MQTT 接收服務啟動失敗${NC}"
    echo -e "  → 查看日誌: tail -50 $WORK_DIR/mqtt.log"
    cleanup
    exit 1
fi

# ============================================================
# 步驟 4: 啟動 Web UI 服務
# ============================================================
echo -e "${YELLOW}[步驟 4/4]${NC} 啟動 Web UI 服務..."

python3 web_manager.py > web.log 2>&1 &
WEB_PID=$!
sleep 3

if ps -p $WEB_PID > /dev/null; then
    echo -e "${GREEN}  ✓ Web UI 服務已啟動 (PID: $WEB_PID)${NC}"
    echo -e "  → 日誌文件: $WORK_DIR/web.log"
    echo "$WEB_PID" > "$WORK_DIR/.web.pid"
    
    # 獲取 IP 地址
    IP=$(hostname -I | awk '{print $1}')
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}  🎉 系統啟動成功！${NC}"
    echo -e "${GREEN}============================================================${NC}\n"
    echo -e "  ${CYAN}Web UI 訪問地址:${NC}"
    echo -e "    → http://localhost:5000"
    echo -e "    → http://${IP}:5000\n"
    echo -e "  ${CYAN}服務狀態:${NC}"
    echo -e "    → MQTT 接收: PID ${MQTT_PID}"
    echo -e "    → Web UI:    PID ${WEB_PID}\n"
    echo -e "  ${CYAN}管理命令:${NC}"
    echo -e "    → 查看 MQTT 日誌: tail -f $WORK_DIR/mqtt.log"
    echo -e "    → 查看 Web 日誌:  tail -f $WORK_DIR/web.log"
    echo -e "    → ${YELLOW}按 Ctrl+C 停止所有服務${NC}\n"
else
    echo -e "${RED}  ✗ Web UI 服務啟動失敗${NC}"
    echo -e "  → 查看日誌: tail -50 $WORK_DIR/web.log"
    cleanup
    exit 1
fi

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  系統運行中... (按 Ctrl+C 停止)${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# ============================================================
# 保持腳本運行，等待用戶中斷
# ============================================================
while true; do
    # 檢查服務是否還在運行
    if ! ps -p $MQTT_PID > /dev/null 2>&1; then
        echo -e "\n${RED}[錯誤] MQTT 接收服務已停止${NC}"
        echo -e "查看日誌: tail -50 $WORK_DIR/mqtt.log"
        cleanup
        exit 1
    fi
    
    if ! ps -p $WEB_PID > /dev/null 2>&1; then
        echo -e "\n${RED}[錯誤] Web UI 服務已停止${NC}"
        echo -e "查看日誌: tail -50 $WORK_DIR/web.log"
        cleanup
        exit 1
    fi
    
    sleep 5
done

