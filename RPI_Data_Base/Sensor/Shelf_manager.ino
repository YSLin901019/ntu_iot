// ==================== shelf_manager.ino ====================
// 貨架管理核心（支援啟用/停用）：初始化、讀取感測器
// 說明：只掃描啟用狀態的貨架，支援配置持久化
// =========================================================

// ---------- 從 flash 載入貨架配置 ----------
void loadShelfConfig() {
  Serial.println("[Config] 正在從 flash 記憶體載入貨架配置...");
  
  // 開啟 Preferences（命名空間：shelf）
  preferences.begin("shelf", false);
  
  int loadedCount = 0;
  
  // 為每個貨架載入啟用狀態
  for (int i = 0; i < SHELF_COUNT; i++) {
    // 使用貨架 ID 作為 key（例如："A1", "B2"）
    String key = String(shelfConfig[i].id);
    
    // 讀取儲存的狀態（預設為 false）
    bool savedEnabled = preferences.getBool(key.c_str(), false);
    
    // 套用載入的配置
    shelfConfig[i].enabled = savedEnabled;
    
    if (savedEnabled) {
      loadedCount++;
      Serial.print("[Config] ✓ ");
      Serial.print(shelfConfig[i].id);
      Serial.println(" 已啟用");
    }
  }
  
  preferences.end();
  
  Serial.print("[Config] 載入完成，已啟用貨架數量: ");
  Serial.print(loadedCount);
  Serial.print(" / ");
  Serial.println(SHELF_COUNT);
}

// ---------- 保存單一貨架配置到 flash ----------
void saveShelfConfig(int shelfIndex) {
  if (shelfIndex < 0 || shelfIndex >= SHELF_COUNT) {
    return;
  }
  
  preferences.begin("shelf", false);
  
  String key = String(shelfConfig[shelfIndex].id);
  preferences.putBool(key.c_str(), shelfConfig[shelfIndex].enabled);
  
  preferences.end();
  
  Serial.print("[Config] 已保存配置: ");
  Serial.print(shelfConfig[shelfIndex].id);
  Serial.print(" = ");
  Serial.println(shelfConfig[shelfIndex].enabled ? "啟用" : "停用");
}

// ---------- 清除所有保存的配置 ----------
void clearAllShelfConfig() {
  preferences.begin("shelf", false);
  preferences.clear();
  preferences.end();
  
  Serial.println("[Config] 已清除所有保存的貨架配置");
}

// ---------- 初始化所有貨架感測器 ----------
void setupShelf() {
    Serial.println("[Shelf] 正在初始化貨架感測器...");
    
    int enabledCount = 0;
    
    // 動態建立所有感測器物件（包含停用的，方便後續動態啟用）
    for (int i = 0; i < SHELF_COUNT; i++) {
      sensors[i] = new Ultrasonic(shelfConfig[i].pin);
      
      Serial.print("[Shelf] 格子 ");
      Serial.print(i);
      Serial.print(" [");
      Serial.print(shelfConfig[i].id);
      Serial.print("] - GPIO:");
      Serial.print(shelfConfig[i].pin);
      
      if (shelfConfig[i].enabled) {
        Serial.println(" ✓ 已啟用");
        enabledCount++;
      } else {
        Serial.println(" ✗ 停用");
      }
    }
    
    Serial.print("[Shelf] 貨架感測器初始化完成，啟用數量: ");
    Serial.print(enabledCount);
    Serial.print(" / ");
    Serial.println(SHELF_COUNT);
  }
  
  // ---------- 根據貨架編號取得索引 ----------
  int getShelfIndexById(const char* shelfId) {
    for (int i = 0; i < SHELF_COUNT; i++) {
      if (strcmp(shelfConfig[i].id, shelfId) == 0) {
        return i;
      }
    }
    return -1;  // 找不到
  }
  
  // ---------- 取得貨架編號 ----------
  const char* getShelfId(int shelfIndex) {
    if (shelfIndex < 0 || shelfIndex >= SHELF_COUNT) {
      return "UNKNOWN";
    }
    return shelfConfig[shelfIndex].id;
  }
  
  // ---------- 檢查貨架是否啟用 ----------
  bool isShelfEnabled(int shelfIndex) {
    if (shelfIndex < 0 || shelfIndex >= SHELF_COUNT) {
      return false;
    }
    return shelfConfig[shelfIndex].enabled;
  }
  
  // ---------- 動態啟用/停用貨架 ----------
  void setShelfEnabled(int shelfIndex, bool enabled) {
    if (shelfIndex >= 0 && shelfIndex < SHELF_COUNT) {
      shelfConfig[shelfIndex].enabled = enabled;
      
      Serial.print("[Shelf] 貨架 ");
      Serial.print(shelfConfig[shelfIndex].id);
      Serial.print(enabled ? " 已啟用" : " 已停用");
      Serial.println();
      
      // 自動保存到 flash 記憶體
      saveShelfConfig(shelfIndex);
    }
  }
  
  // ---------- 讀取所有啟用貨架的感測器數值 ----------
  void readAllShelfSensors() {
    for (int i = 0; i < SHELF_COUNT; i++) {
      // 只讀取啟用的貨架
      if (!shelfConfig[i].enabled) {
        distance[i] = -1;  // 停用的貨架標記為 -1
        continue;
      }
      
      // 讀取感測器（毫米）
      long dist = sensors[i]->MeasureInMillimeters();
      delay(35);  // 等待測量完成
      
      // 濾除異常值（範圍：20-4000 mm）
      if (dist < 20 || dist > 4000) {
        dist = -1;
      }
      
      // 儲存讀值
      distance[i] = dist;
    }
  }
  
  // ---------- 印出所有感測器讀值 ----------
  void printAllSensorReadings() {
    Serial.println("========== 感測器讀值 ==========");
    
    for (int i = 0; i < SHELF_COUNT; i++) {
      // 只顯示啟用的貨架
      if (!shelfConfig[i].enabled) {
        continue;
      }
      
      Serial.print("[");
      Serial.print(shelfConfig[i].id);
      Serial.print("] 格子 ");
      Serial.print(i);
      Serial.print(": ");
      
      if (distance[i] == -1) {
        Serial.println("感測器錯誤");
        continue;
      }
      
      Serial.print("距離=");
      Serial.print(distance[i] / 10.0, 1);
      Serial.println("cm");
    }
    
    Serial.println("===============================");
  }
  