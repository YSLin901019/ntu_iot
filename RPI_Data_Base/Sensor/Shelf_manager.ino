// ==================== shelf_manager.ino ====================
// 貨架管理核心（支援啟用/停用）：初始化、讀取感測器
// 說明：只掃描啟用狀態的貨架
// =========================================================

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
  