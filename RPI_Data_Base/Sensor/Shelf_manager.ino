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
  
  // 為每個貨架載入啟用狀態和貨架長度
  for (int i = 0; i < SHELF_COUNT; i++) {
    // 使用貨架 ID 作為 key（例如："A1", "B2"）
    String key = String(shelfConfig[i].id);
    
    // 讀取儲存的狀態（預設為 false）
    bool savedEnabled = preferences.getBool(key.c_str(), false);
    
    // 讀取儲存的貨架長度（預設為 0.0）
    String lengthKey = key + "_len";
    float savedLength = preferences.getFloat(lengthKey.c_str(), 0.0);
    
    // 套用載入的配置
    shelfConfig[i].enabled = savedEnabled;
    shelfConfig[i].shelf_length = savedLength;
    
    if (savedEnabled) {
      loadedCount++;
      Serial.print("[Config] ✓ ");
      Serial.print(shelfConfig[i].id);
      Serial.print(" 已啟用");
      if (savedLength > 0) {
        Serial.print(", 長度: ");
        Serial.print(savedLength, 1);
        Serial.print("cm");
      }
      Serial.println();
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
  
  // 同時保存貨架長度
  String lengthKey = key + "_len";
  preferences.putFloat(lengthKey.c_str(), shelfConfig[shelfIndex].shelf_length);
  
  preferences.end();
  
  Serial.print("[Config] 已保存配置: ");
  Serial.print(shelfConfig[shelfIndex].id);
  Serial.print(" = ");
  Serial.print(shelfConfig[shelfIndex].enabled ? "啟用" : "停用");
  if (shelfConfig[shelfIndex].shelf_length > 0) {
    Serial.print(", 長度: ");
    Serial.print(shelfConfig[shelfIndex].shelf_length, 1);
    Serial.print("cm");
  }
  Serial.println();
}

// ---------- 清除所有保存的配置 ----------
void clearAllShelfConfig() {
  preferences.begin("shelf", false);
  preferences.clear();
  preferences.end();
  
  Serial.println("[Config] 已清除所有保存的貨架配置");
}

// ---------- 貨架校正功能（測量空貨架長度）----------
float calibrateShelf(int shelfIndex) {
  if (shelfIndex < 0 || shelfIndex >= SHELF_COUNT) {
    Serial.println("[Calibrate] ✗ 無效的貨架索引");
    return -1.0;
  }
  
  Serial.print("[Calibrate] 開始校正貨架 ");
  Serial.print(shelfConfig[shelfIndex].id);
  Serial.println(" ...");
  Serial.println("[Calibrate] 請確保貨架上沒有任何物品！");
  Serial.println("[Calibrate] 正在進行 10 次測量...");
  
  const int CALIBRATE_SAMPLES = 10;
  float validReadings[CALIBRATE_SAMPLES];
  int validCount = 0;
  
  for (int i = 0; i < CALIBRATE_SAMPLES; i++) {
    long distMm = sensors[shelfIndex]->MeasureInMillimeters();
    float distCm = distMm / 10.0;
    
    Serial.print("[Calibrate] 測量 #");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(distCm, 1);
    Serial.print(" cm");
    
    // 檢查是否為有效讀值（20mm - 4000mm，即 2-400cm）
    if (distMm >= 20 && distMm <= 4000) {
      validReadings[validCount] = distCm;
      validCount++;
      Serial.println(" ✓");
    } else {
      Serial.println(" ✗ 無效");
    }
    
    delay(100);  // 等待下次測量
  }
  
  // 檢查是否有足夠的有效讀值
  if (validCount < 5) {
    Serial.print("[Calibrate] ✗ 校正失敗：有效測量次數不足 (");
    Serial.print(validCount);
    Serial.println("/10)");
    return -1.0;
  }
  
  // 計算平均值
  float sum = 0;
  for (int i = 0; i < validCount; i++) {
    sum += validReadings[i];
  }
  float average = sum / validCount;
  
  // 保存到配置並持久化
  shelfConfig[shelfIndex].shelf_length = average;
  saveShelfConfig(shelfIndex);
  
  Serial.println();
  Serial.print("[Calibrate] ✓ 校正完成！貨架 ");
  Serial.print(shelfConfig[shelfIndex].id);
  Serial.print(" 長度: ");
  Serial.print(average, 1);
  Serial.print(" cm (");
  Serial.print(validCount);
  Serial.println(" 次有效測量)");
  
  return average;
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
  