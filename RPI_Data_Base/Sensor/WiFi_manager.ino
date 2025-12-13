// ==================== wifi_manager.ino ====================
// ESP32 永久自動連 Wi-Fi + 隨時可印狀態
// =========================================================

// 把你的 Wi-Fi 資訊寫在這裡（之後要多組也可以改成陣列）
const char* ssid     = "KamPus-2";
const char* password = "2392036202";

// 內部狀態變數
static bool wifiConnected = false;
unsigned long lastAttemptTime = 0;
unsigned long lastCheckTime = 0;
const unsigned long RECONNECT_INTERVAL = 50000;

// 函式前向宣告
void printWiFiStatus();
void CheckWiFiConnection();
void ConnectWiFi();

// 呼叫一次就開始自動連線
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  // 進行第一次連線
  unsigned long start = millis();
  while (millis() - start < 10000) {
    if (WiFi.status() == WL_CONNECTED) {
      wifiConnected = true;
      printWiFiStatus();
      return;
    } else {
      wifiConnected = false;
      printWiFiStatus();
      return;
    }
  }
}

void HostWiFiManager() {
  // 每分鐘，檢查一次 WiFi 連線狀態
  if (millis() - lastCheckTime >= 60000) {
    lastCheckTime = millis();
    CheckWiFiConnection();
  }

  if (wifiConnected) {
    return;
  } else {
    ConnectWiFi();
    return;
  }
}

void CheckWiFiConnection() {
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    printWiFiStatus();
  } else if (WiFi.status() == WL_DISCONNECTED) {
    wifiConnected = false;
    printWiFiStatus();
  }
}

void ConnectWiFi() {
  WiFi.begin(ssid, password);
  unsigned long start = millis();
  while (millis() - start < 10000) {
    if (WiFi.status() == WL_CONNECTED) {
      wifiConnected = true;
      printWiFiStatus();
      return;
    }
  }
}

void printWiFiStatus() {
  Serial.println("========== 目前 WiFi 狀態 ==========");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("狀態: 已連線");
    Serial.print("SSID: ");          Serial.println(WiFi.SSID());
    Serial.print("IP: ");            Serial.println(WiFi.localIP());
    Serial.print("RSSI: ");          Serial.print(WiFi.RSSI()); Serial.println(" dBm");
    // Serial.print("MAC: ");           Serial.println(WiFi.macAddress());
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