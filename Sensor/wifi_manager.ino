// ==================== wifi_manager.ino ====================
// ESP32 永久自動連 Wi-Fi + 隨時可印狀態
// =========================================================

#include <WiFi.h>

// 把你的 Wi-Fi 資訊寫在這裡（之後要多組也可以改成陣列）
const char* ssid     = "iPhone";
const char* password = "5603901019";

// 內部狀態變數
static bool wifiConnected = false;
static unsigned long lastAttemptTime = 0;
const unsigned long RECONNECT_INTERVAL = 8000;   // 失敗後每 8 秒重試一次

// =========================================================
// 呼叫一次就開始自動連線（放在 setup() 裡）
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  Serial.print("[WiFi] 正在連線到 ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  // 第一次先等 10 秒（給比較穩的連線機會）
  unsigned long start = millis();
  while (millis() - start < 100000) {
    if (WiFi.status() == WL_CONNECTED) {
      wifiConnected = true;
      printConnectedInfo();
      return;
    }
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("[WiFi] 第一次連線失敗，進入背景持續重試模式...");
}

// =========================================================
// 一定要放在 loop() 裡（非阻塞持續重試）
void handleWiFiConnection() {
  if (wifiConnected && WiFi.status() == WL_CONNECTED) {
    // 已經連上且還在線上 → 什麼都不做
    return;
  }

  // 斷線或還沒連上 → 看是不是該重試了
  if (millis() - lastAttemptTime >= RECONNECT_INTERVAL) {
    lastAttemptTime = millis();

    Serial.print("[WiFi] 正在重新連線 ");
    Serial.println(ssid);

    WiFi.disconnect();       // 先斷開舊的殘餘連線
    WiFi.begin(ssid, password);

    // 這次只等 8 秒
    unsigned long start = millis();
    while (millis() - start < 8000) {
      if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        printConnectedInfo();
        return;
      }
      delay(500);
      Serial.print(".");
    }
    Serial.println(" 失敗，8秒後再試");
  }
}

// =========================================================
// 成功連上後印出詳細資訊（只印一次）
void printConnectedInfo() {
  Serial.println();
  Serial.println("WiFi 已成功連線！");
  Serial.print("IP 位址: "); Serial.println(WiFi.localIP());
  Serial.print("訊號強度: "); Serial.print(WiFi.RSSI()); Serial.println(" dBm");
  Serial.println("========================================");
}

// =========================================================
// 隨時呼叫就會印出目前網路狀態（連上或沒連上都行）
void printWiFiStatus() {
  Serial.println("========== 目前 WiFi 狀態 ==========");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("狀態: 已連線");
    Serial.print("SSID: ");          Serial.println(WiFi.SSID());
    Serial.print("IP: ");            Serial.println(WiFi.localIP());
    Serial.print("RSSI: ");          Serial.print(WiFi.RSSI()); Serial.println(" dBm");
    Serial.print("MAC: ");           Serial.println(WiFi.macAddress());
  } else {
    Serial.println("狀態: 未連線");
    switch (WiFi.status()) {
      case WL_NO_SSID_AVAIL:    Serial.println("原因: 找不到 SSID"); break;
      case WL_CONNECT_FAILED:   Serial.println("原因: 密碼錯誤或訊號太弱"); break;
      case WL_CONNECTION_LOST:  Serial.println("原因: 連線中斷"); break;
      case WL_DISCONNECTED:     Serial.println("原因: 已斷線"); break;
      default:                  Serial.println("原因: 其他"); break;
    }
  }
  Serial.println("====================================");
}