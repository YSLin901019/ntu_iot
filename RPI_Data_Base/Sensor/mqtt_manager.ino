// ==================== mqtt_manager.ino ====================
// MQTT 管理器（簡化版）：連線、發布原始感測器數據
// 說明：只發送原始數據，不做任何判斷
// mqtt_server: 192.168.0.109
// =========================================================

// ---------- MQTT 伺服器設定 ----------
const char* mqtt_server = "192.168.0.109";  // 請改成你的 RPI IP 位址
const int mqtt_port = 1883;                 // MQTT 預設埠號
const char* mqtt_user = "";                 // MQTT 使用者名稱（如果有設定）
const char* mqtt_password = "";             // MQTT 密碼（如果有設定）

// ---------- MQTT 主題設定 ----------
const char* mqtt_topic_sensor = "shelf/sensor";      // 感測器數據主題
const char* mqtt_topic_status = "shelf/status";      // 狀態主題
const char* mqtt_topic_command = "shelf/command";    // 命令主題（訂閱）
const char* mqtt_topic_discovery = "shelf/discovery";  // 設備探測主題（訂閱）
const char* mqtt_topic_discovery_response = "shelf/discovery/response";  // 設備探測回應主題
const char* mqtt_topic_heartbeat = "shelf/heartbeat";  // 心跳檢測主題（訂閱）
const char* mqtt_topic_heartbeat_response = "shelf/heartbeat/response";  // 心跳檢測回應主題
const char* mqtt_topic_shelf_config_request = "shelf/config/request";  // 貨架配置查詢主題（訂閱）
const char* mqtt_topic_shelf_config_response = "shelf/config/response";  // 貨架配置回應主題
String serial_number = "";
String device_id = "";

// ---------- MQTT 客戶端 ----------
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ---------- 內部狀態變數 ----------
unsigned long lastMQTTReconnect = 0;
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;  // 5秒重連一次

unsigned long lastStatusPublish = 0;
const unsigned long STATUS_PUBLISH_INTERVAL = 30000;  // 30秒發送一次狀態更新

// ---------- 函式前向宣告 ----------
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();

// Shelf_manager.ino 中的函數
int getShelfIndexById(const char* shelfId);
const char* getShelfId(int shelfIndex);
bool isShelfEnabled(int shelfIndex);
void setShelfEnabled(int shelfIndex, bool enabled);
int getEnabledShelfCount();

void getDeviceId() {
  uint64_t chipid = ESP.getEfuseMac();
  serial_number = String((uint32_t)(chipid >> 32), HEX) + String((uint32_t)chipid, HEX);
  serial_number.toUpperCase();
  device_id = "ESP32S3_" + serial_number;
}

// ---------- 初始化 MQTT ----------
void setupMQTT() {
  // 設置 MQTT 緩衝區大小（預設 256，增加到 1024 以支援較大的 JSON）
  mqttClient.setBufferSize(1024);
  
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);
  
  Serial.println("[MQTT] MQTT 設定完成");
  Serial.print("[MQTT] 緩衝區大小: ");
  Serial.println(mqttClient.getBufferSize());
  Serial.print("[MQTT] 伺服器: ");
  Serial.print(mqtt_server);
  Serial.print(":");
  Serial.println(mqtt_port);
  
  // 嘗試首次連線
  if (WiFi.status() == WL_CONNECTED) {
    reconnectMQTT();
  } else {
    Serial.println("[MQTT] WiFi 未連線，稍後將自動重連 MQTT");
  }
}

// ---------- MQTT 連線處理 ----------
void handleMQTTConnection() {
  // 如果已連線，處理訊息
  if (mqttClient.connected()) {
    mqttClient.loop();
    
    // 定期發送狀態更新
    unsigned long now = millis();
    if (now - lastStatusPublish >= STATUS_PUBLISH_INTERVAL) {
      lastStatusPublish = now;
      publishSystemStatus();
    }
    
    return;
  }
  
  // 如果未連線且 WiFi 已連線，嘗試重連
  if (WiFi.status() == WL_CONNECTED) {
    unsigned long now = millis();
    if (now - lastMQTTReconnect >= MQTT_RECONNECT_INTERVAL) {
      lastMQTTReconnect = now;
      reconnectMQTT();
    }
  }
}

// ---------- MQTT 重新連線 ----------
void reconnectMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[MQTT] WiFi 未連線，無法連接 MQTT");
    return;
  }
  
  Serial.print("[MQTT] 正在連接 MQTT 伺服器...");
  
  // 產生唯一的客戶端 ID
  String clientId = "ESP32_Shelf_";
  clientId += String(random(0xffff), HEX);

  // 嘗試連線
  bool connected = false;
  if (strlen(mqtt_user) > 0) {
    // 有使用者名稱和密碼
    connected = mqttClient.connect(clientId.c_str(), mqtt_user, mqtt_password);
  } else {
    // 無需認證
    connected = mqttClient.connect(clientId.c_str());
  }
  
  if (connected) {
    Serial.println(" 成功！");
    Serial.print("[MQTT] 客戶端 ID: ");
    Serial.println(clientId);
    
    // 訂閱命令主題
    mqttClient.subscribe(mqtt_topic_command);
    Serial.print("[MQTT] 已訂閱主題: ");
    Serial.println(mqtt_topic_command);
    
    // 訂閱設備探測主題
    mqttClient.subscribe(mqtt_topic_discovery);
    Serial.print("[MQTT] 已訂閱主題: ");
    Serial.println(mqtt_topic_discovery);
    
    // 訂閱心跳檢測主題
    mqttClient.subscribe(mqtt_topic_heartbeat);
    Serial.print("[MQTT] 已訂閱主題: ");
    Serial.println(mqtt_topic_heartbeat);
    
    // 訂閱貨架配置查詢主題
    mqttClient.subscribe(mqtt_topic_shelf_config_request);
    Serial.print("[MQTT] 已訂閱主題: ");
    Serial.println(mqtt_topic_shelf_config_request);
    
    // 發送上線訊息
    publishStatus("online");
  } else {
    Serial.print(" 失敗，錯誤碼: ");
    Serial.println(mqttClient.state());
    
    // 錯誤碼說明
    switch (mqttClient.state()) {
      case -4: Serial.println("[MQTT] 連線逾時"); break;
      case -3: Serial.println("[MQTT] 連線中斷"); break;
      case -2: Serial.println("[MQTT] 連線失敗"); break;
      case -1: Serial.println("[MQTT] 已斷線"); break;
      case 1: Serial.println("[MQTT] 協定版本錯誤"); break;
      case 2: Serial.println("[MQTT] 客戶端 ID 被拒"); break;
      case 3: Serial.println("[MQTT] 伺服器無法使用"); break;
      case 4: Serial.println("[MQTT] 使用者名稱或密碼錯誤"); break;
      case 5: Serial.println("[MQTT] 未授權"); break;
      default: Serial.println("[MQTT] 未知錯誤"); break;
    }
  }
}

// ---------- MQTT 訊息回調函式 ----------
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("[MQTT] 收到訊息 [");
  Serial.print(topic);
  Serial.print("]: ");
  
  // 將 payload 轉換成字串
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);
  
  // 處理命令
  if (strcmp(topic, mqtt_topic_command) == 0) {
    handleMQTTCommand(message);
  }
  // 處理設備探測請求
  else if (strcmp(topic, mqtt_topic_discovery) == 0) {
    handleDiscoveryRequest(message);
  }
  // 處理心跳檢測請求
  else if (strcmp(topic, mqtt_topic_heartbeat) == 0) {
    handleHeartbeatRequest(message);
  }
  // 處理貨架配置查詢請求
  else if (strcmp(topic, mqtt_topic_shelf_config_request) == 0) {
    handleShelfConfigRequest(message);
  }
}

// ---------- 處理 MQTT 命令 ----------
void handleMQTTCommand(String command) {
  command.trim();
  command.toLowerCase();
  
  if (command == "status") {
    // 回報系統狀態
    publishSystemStatus();
  } else if (command == "read") {
    // 立即讀取並發送感測器數據
    readAllShelfSensors();
    publishAllSensorData();
  } else if (command.startsWith("enable ")) {
    // 啟用特定貨架（例如："enable A1"）
    String shelfId = command.substring(7);
    shelfId.trim();
    shelfId.toUpperCase();
    
    int idx = getShelfIndexById(shelfId.c_str());
    if (idx >= 0) {
      setShelfEnabled(idx, true);
      publishSystemStatus();  // 回報更新後的狀態
    } else {
      Serial.print("[MQTT] 找不到貨架: ");
      Serial.println(shelfId);
    }
  } else if (command.startsWith("disable ")) {
    // 停用特定貨架（例如："disable A1"）
    String shelfId = command.substring(8);
    shelfId.trim();
    shelfId.toUpperCase();
    
    int idx = getShelfIndexById(shelfId.c_str());
    if (idx >= 0) {
      setShelfEnabled(idx, false);
      publishSystemStatus();  // 回報更新後的狀態
    } else {
      Serial.print("[MQTT] 找不到貨架: ");
      Serial.println(shelfId);
    }
  } else {
    Serial.print("[MQTT] 未知命令: ");
    Serial.println(command);
  }
}

// ---------- 發布狀態訊息 ----------
void publishStatus(const char* status) {
  if (!mqttClient.connected()) {
    return;
  }
  
  mqttClient.publish(mqtt_topic_status, status);
  Serial.print("[MQTT] 已發布狀態: ");
  Serial.println(status);
}

// ---------- 發布系統狀態 ----------
void publishSystemStatus() {
  if (!mqttClient.connected()) {
    return;
  }
  
  // 建立 JSON 格式的系統狀態（包含 device_id）
  String json = "{";
  json += "\"device_id\":\"" + device_id + "\",";
  json += "\"wifi\":\"";
  json += (WiFi.status() == WL_CONNECTED) ? "connected" : "disconnected";
  json += "\",\"mqtt\":\"connected\"";
  json += ",\"uptime_ms\":";
  json += millis();
  json += ",\"shelf_count\":";
  json += SHELF_COUNT;
  json += ",\"enabled_shelf_count\":";
  json += getEnabledShelfCount();
  json += "}";
  
  mqttClient.publish(mqtt_topic_status, json.c_str());
  Serial.println("[MQTT] 已發布系統狀態");
}

// ---------- 發布單一感測器數據 ----------
void publishSensorData(int shelfIndex) {
  if (!mqttClient.connected()) {
    return;
  }
  
  if (shelfIndex < 0 || shelfIndex >= SHELF_COUNT) {
    return;
  }
  
  // 只發布啟用的貨架數據
  if (!shelfConfig[shelfIndex].enabled) {
    return;
  }
  
  // 將距離從 mm 轉換成 cm（保留小數點後一位）
  float distCm = distance[shelfIndex] / 10.0;
  
  // 建立 JSON 格式的感測器數據（只有原始讀值）
  char json[256];
  snprintf(json, sizeof(json), 
           "{\"device_id\":\"%s\",\"shelf_id\":\"%s\",\"index\":%d,\"distance_cm\":%.1f,\"enabled\":true}",
           device_id.c_str(), shelfConfig[shelfIndex].id, shelfIndex, distCm);
  
  mqttClient.publish(mqtt_topic_sensor, json);
  Serial.print("[MQTT] 已發布感測器數據: ");
  Serial.println(shelfConfig[shelfIndex].id);
}

// ---------- 發布所有感測器數據 ----------
void publishAllSensorData() {
  if (!mqttClient.connected()) {
    return;
  }
  
  int publishedCount = 0;
  
  for (int i = 0; i < SHELF_COUNT; i++) {
    // 只發布啟用的貨架
    if (shelfConfig[i].enabled) {
      publishSensorData(i);
      publishedCount++;
      delay(100);  // 避免訊息太密集
    }
  }
  
  Serial.print("[MQTT] 已發布 ");
  Serial.print(publishedCount);
  Serial.println(" 個啟用貨架的感測器數據");
}

// ---------- 檢查 MQTT 連線狀態 ----------
bool isMQTTConnected() {
  return mqttClient.connected();
}

// ---------- 處理設備探測請求 ----------
void handleDiscoveryRequest(String message) {
  Serial.println("[Discovery] 收到設備探測請求");
  
  // 建立回應 JSON
  String response = "{";
  
  // 設備 ID
  response += "\"device_id\":\"" + device_id + "\",";
  
  // 設備名稱（可自定義）
  response += "\"device_name\":\"ESP32S3 設備\",";
  
  // 可用貨架列表（只列出啟用的貨架）
  response += "\"shelves\":[";
  bool firstShelf = true;
  for (int i = 0; i < SHELF_COUNT; i++) {
    if (shelfConfig[i].enabled) {
      if (!firstShelf) response += ",";
      response += "\"" + String(shelfConfig[i].id) + "\"";
      firstShelf = false;
    }
  }
  response += "],";
  
  // 貨架總數和啟用數
  response += "\"total_shelves\":" + String(SHELF_COUNT) + ",";
  response += "\"enabled_shelves\":" + String(getEnabledShelfCount()) + ",";
  
  // WiFi 信號強度
  int rssi = WiFi.RSSI();
  response += "\"wifi_signal\":" + String(rssi) + ",";
  
  // 運行時間（毫秒）
  response += "\"uptime_ms\":" + String(millis());
  
  response += "}";
  
  // 發送回應到設備探測回應主題
  if (mqttClient.connected()) {
    mqttClient.publish(mqtt_topic_discovery_response, response.c_str());
    Serial.println("[Discovery] 已發送設備資訊:");
    Serial.println(response);
  } else {
    Serial.println("[Discovery] MQTT 未連線，無法發送回應");
  }
}

// ---------- 處理心跳檢測請求 ----------
void handleHeartbeatRequest(String message) {
  Serial.println("[Heartbeat] 收到心跳檢測請求");
  
  // 建立心跳回應 JSON
  String response = "{";
  response += "\"device_id\":\"" + device_id + "\",";
  response += "\"status\":\"online\",";
  response += "\"timestamp\":" + String(millis());
  response += "}";
  
  // 發送心跳回應
  if (mqttClient.connected()) {
    mqttClient.publish(mqtt_topic_heartbeat_response, response.c_str());
    Serial.println("[Heartbeat] 已發送心跳回應");
  } else {
    Serial.println("[Heartbeat] MQTT 未連線，無法發送回應");
  }
}

// ---------- 處理貨架配置查詢請求 ----------
void handleShelfConfigRequest(String message) {
  Serial.println("[ShelfConfig] 收到貨架配置查詢請求");
  Serial.print("[ShelfConfig] 訊息內容: ");
  Serial.println(message);
  Serial.print("[ShelfConfig] 本機 device_id: ");
  Serial.println(device_id);
  
  // 檢查是否指定了特定設備
  // 訊息格式: {"device_id": "ESP32S3_XXXX"}
  if (message.length() > 0 && message.indexOf(device_id) < 0 && message.indexOf("\"device_id\"") >= 0) {
    // 如果訊息指定了設備ID但不是本設備，忽略
    Serial.println("[ShelfConfig] 查詢目標不是本設備，忽略");
    return;
  }
  
  Serial.println("[ShelfConfig] 開始建立回應 JSON...");
  
  // 建立貨架配置回應 JSON
  String response = "{";
  response += "\"device_id\":\"" + device_id + "\",";
  
  // 貨架配置列表
  response += "\"shelves\":[";
  for (int i = 0; i < SHELF_COUNT; i++) {
    if (i > 0) response += ",";
    response += "{";
    response += "\"shelf_id\":\"" + String(shelfConfig[i].id) + "\",";
    response += "\"index\":" + String(i) + ",";
    response += "\"gpio\":" + String(shelfConfig[i].pin) + ",";
    response += "\"enabled\":" + String(shelfConfig[i].enabled ? "true" : "false");
    response += "}";
  }
  response += "],";
  
  response += "\"total_count\":" + String(SHELF_COUNT) + ",";
  response += "\"enabled_count\":" + String(getEnabledShelfCount());
  response += "}";
  
  Serial.println("[ShelfConfig] JSON 建立完成");
  Serial.print("[ShelfConfig] JSON 長度: ");
  Serial.println(response.length());
  
  // 發送貨架配置回應
  if (mqttClient.connected()) {
    Serial.print("[ShelfConfig] 正在發送到主題: ");
    Serial.println(mqtt_topic_shelf_config_response);
    
    bool result = mqttClient.publish(mqtt_topic_shelf_config_response, response.c_str());
    
    if (result) {
      Serial.println("[ShelfConfig] ✓ 貨架配置已成功發送");
      Serial.println("[ShelfConfig] 發送內容:");
      Serial.println(response);
    } else {
      Serial.println("[ShelfConfig] ✗ 發送失敗");
    }
  } else {
    Serial.println("[ShelfConfig] ✗ MQTT 未連線，無法發送回應");
  }
}
