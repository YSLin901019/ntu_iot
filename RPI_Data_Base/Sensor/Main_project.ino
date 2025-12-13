// ==================== Main_project.ino ====================
// ESP32 S3 貨架監控系統主程式（簡化版）
// 功能：WiFi、MQTT、超音波感測
// 說明：ESP32 只負責收集感測器數據並發送到 RPI
//       所有判斷邏輯和數據庫由 RPI 處理
// =========================================================

#include <WiFi.h>
#include <PubSubClient.h>
#include "Ultrasonic.h"

// ---------- 全域計時器 ----------
unsigned long lastSensorRead = 0;
const unsigned long SENSOR_READ_INTERVAL = 5000;  // 每5秒讀取一次感測器

// ---------- 系統初始化 ----------
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  getDeviceId();
  
  Serial.println("\n\n========================================");
  Serial.println("   ESP32 S3 感測器節點啟動中...");
  Serial.println("   (簡化版 - 僅數據收集)");
  Serial.println("========================================\n");
  
  // 1. 初始化 WiFi
  Serial.println(">>> 步驟 1: 初始化 WiFi");
  setupWiFi();
  
  // 2. 初始化 MQTT
  Serial.println("\n>>> 步驟 2: 初始化 MQTT");
  setupMQTT();
  
  // 3. 初始化貨架感測器
  Serial.println("\n>>> 步驟 3: 初始化貨架感測器");
  setupShelf();
  
  Serial.println("\n========================================");
  Serial.println("   系統初始化完成！");
  Serial.println("   開始發送感測器數據到 RPI...");
  Serial.println("========================================\n");
  
  delay(1000);
}

// ---------- 主迴圈 ----------
void loop() {
  // 處理 WiFi 連線
  HostWiFiManager();
  
  // 處理 MQTT 連線
  handleMQTTConnection();
  
  // 定期讀取感測器並立即發送到 RPI
  if (millis() - lastSensorRead >= SENSOR_READ_INTERVAL) {
    lastSensorRead = millis();
    
    // 讀取所有感測器
    readAllShelfSensors();
    
    // 立即發送到 RPI（不做任何判斷）
    if (isMQTTConnected()) {
      publishAllSensorData();
    }
  }
  delay(10);  // 避免 watchdog 重置
}

