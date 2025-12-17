// ==================== wifi_manager.ino ====================
// ESP32 自動連 Wi-Fi - 支援多組 Wi-Fi 輪流嘗試
// =========================================================

// ✅ 多 Wi-Fi 配置結構
struct WiFiCredential {
  const char* ssid;
  const char* password;
};

// ✅ 在這裡添加你的 Wi-Fi 網路（優先順序由上到下）
const WiFiCredential wifiList[] = {
  {"KamPus-2", "2392036202"},
  {"iWave", "33366526"},   
};

const int WIFI_COUNT = sizeof(wifiList) / sizeof(wifiList[0]);  // 自動計算 WiFi 數量

// 內部狀態變數
static bool wifiConnected = false;
static int lastSuccessfulWiFiIndex = 0;  // 記錄上次成功連線的 WiFi 索引
static int currentTryIndex = 0;           // 當前嘗試的 WiFi 索引
unsigned long lastAttemptTime = 0;
unsigned long lastCheckTime = 0;
const unsigned long RECONNECT_INTERVAL = 50000;
const unsigned long SINGLE_WIFI_TIMEOUT = 10000;  // 單個 WiFi 嘗試超時時間（10秒）

// 函式前向宣告
void printWiFiStatus();
void CheckWiFiConnection();
void ConnectWiFi();
void ConnectToWiFi(int wifiIndex);
bool TryConnectWiFi(const char* ssid, const char* password, unsigned long timeout);

// ✅ 初始化 WiFi - 會輪流嘗試所有配置的 WiFi
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);  // 關閉自動重連，由我們手動控制
  
  Serial.println();
  Serial.println("========================================");
  Serial.println("[WiFi] 開始連線...");
  Serial.print("[WiFi] 已配置 ");
  Serial.print(WIFI_COUNT);
  Serial.println(" 組 WiFi");
  Serial.println("========================================");
  
  // 輪流嘗試所有 WiFi，直到成功或全部失敗
  for (int i = 0; i < WIFI_COUNT; i++) {
    int tryIndex = (lastSuccessfulWiFiIndex + i) % WIFI_COUNT;  // 從上次成功的開始
    
    Serial.println();
    Serial.print("[WiFi] 嘗試連線 (");
    Serial.print(i + 1);
    Serial.print("/");
    Serial.print(WIFI_COUNT);
    Serial.print("): ");
    Serial.println(wifiList[tryIndex].ssid);
    
    if (TryConnectWiFi(wifiList[tryIndex].ssid, wifiList[tryIndex].password, SINGLE_WIFI_TIMEOUT)) {
      wifiConnected = true;
      lastSuccessfulWiFiIndex = tryIndex;
      currentTryIndex = tryIndex;
      Serial.println();
      Serial.println("========================================");
      Serial.println("[WiFi] ✓ 連線成功！");
      Serial.println("========================================");
      printWiFiStatus();
      return;
    }
  }
  
  // 所有 WiFi 都失敗
  wifiConnected = false;
  Serial.println();
  Serial.println("========================================");
  Serial.println("[WiFi] ✗ 所有 WiFi 連線失敗");
  Serial.println("[WiFi] 稍後將自動重試...");
  Serial.println("========================================");
  printWiFiStatus();
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

// ✅ 嘗試連線到所有配置的 WiFi（輪流嘗試）
void ConnectWiFi() {
  Serial.println();
  Serial.println("[WiFi] 開始重新連線...");
  
  // 輪流嘗試所有 WiFi
  for (int i = 0; i < WIFI_COUNT; i++) {
    int tryIndex = (lastSuccessfulWiFiIndex + i) % WIFI_COUNT;  // 從上次成功的開始
    
    Serial.print("[WiFi] 嘗試連線 (");
    Serial.print(i + 1);
    Serial.print("/");
    Serial.print(WIFI_COUNT);
    Serial.print("): ");
    Serial.println(wifiList[tryIndex].ssid);
    
    if (TryConnectWiFi(wifiList[tryIndex].ssid, wifiList[tryIndex].password, SINGLE_WIFI_TIMEOUT)) {
      wifiConnected = true;
      lastSuccessfulWiFiIndex = tryIndex;
      currentTryIndex = tryIndex;
      Serial.println("[WiFi] ✓ 重新連線成功！");
      printWiFiStatus();
      return;
    }
  }
  
  // 所有 WiFi 都失敗
  wifiConnected = false;
  Serial.println("[WiFi] ✗ 所有 WiFi 重連失敗");
}

// ✅ 嘗試連線到指定的 WiFi（帶超時）
bool TryConnectWiFi(const char* ssid, const char* password, unsigned long timeout) {
  WiFi.disconnect(true);  // 先斷開現有連線
  delay(100);
  
  WiFi.begin(ssid, password);
  
  unsigned long start = millis();
  while (millis() - start < timeout) {
    if (WiFi.status() == WL_CONNECTED) {
      return true;  // 連線成功
    }
    delay(100);  // 短暫延遲避免CPU過載
  }
  
  return false;  // 超時，連線失敗
}

void printWiFiStatus() {
  Serial.println();
  Serial.println("========== 目前 WiFi 狀態 ==========");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("狀態: ✓ 已連線");
    Serial.print("SSID: ");          
    Serial.print(WiFi.SSID());
    Serial.print(" (配置 #");
    Serial.print(lastSuccessfulWiFiIndex + 1);
    Serial.println(")");
    Serial.print("IP: ");            Serial.println(WiFi.localIP());
    Serial.print("訊號強度: ");      Serial.print(WiFi.RSSI()); Serial.println(" dBm");
    Serial.print("MAC: ");           Serial.println(WiFi.macAddress());
  } else {
    Serial.println("狀態: ✗ 未連線");
    switch (WiFi.status()) {
      case WL_NO_SSID_AVAIL:    Serial.println("原因: 找不到 SSID"); break;
      case WL_CONNECT_FAILED:   Serial.println("原因: 密碼錯誤或訊號太弱"); break;
      case WL_CONNECTION_LOST:  Serial.println("原因: 連線中斷"); break;
      case WL_DISCONNECTED:     Serial.println("原因: 已斷線"); break;
      default:                  Serial.println("原因: 其他"); break;
    }
    Serial.println();
    Serial.println("📋 已配置的 WiFi 列表:");
    for (int i = 0; i < WIFI_COUNT; i++) {
      Serial.print("  ");
      Serial.print(i + 1);
      Serial.print(". ");
      Serial.print(wifiList[i].ssid);
      if (i == lastSuccessfulWiFiIndex) {
        Serial.print(" ⭐ (上次成功)");
      }
      Serial.println();
    }
  }
  Serial.println("====================================");
  Serial.println();
}