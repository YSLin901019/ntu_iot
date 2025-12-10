// ==================== shelf_manager.ino ====================
// 貨架管理核心：初始化 + 更新 + 判斷
// ========================================================

void setupShelf() {
  // 動態建立所有感測器物件（關鍵！）
  for (int i = 0; i < SHELF_COUNT; i++) {
    sensorFront[i] = new Ultrasonic(pinFront[i]);
    sensorBack[i]  = new Ultrasonic(pinBack[i]);
  }
  Serial.printf("[Shelf] 貨架管理系統啟動，總共 %d 格\n", SHELF_COUNT);
}

// 關鍵函數：一次呼叫就掃完全部貨架（前後雙感測器）
void updateShelfSensors() {
  for (int i = 0; i < SHELF_COUNT; i++) {
    // 讀取這一格的前後距離
    long f = sensorFront[i]->MeasureInCentimeters();
    delay(35);   // 重要！兩顆之間要錯開，避免干擾（35ms 超穩）
    long b = sensorBack[i]->MeasureInCentimeters();
    delay(35);   // 下一格前再留一點緩衝

    // 濾異常值
    if (f <= 0 || f > 400) f = 999;
    if (b <= 0 || b > 400) b = 999;

    distFront[i] = f;
    distBack[i]  = b;

    float depth = shelfDepth[i];

    // 判断是否有货
    if (f < depth * 0.9) {
      shelfOccupied[i] = true;
      shelfFillPercent[i] = min(min(f, b) / depth * 100.0f, 100.0f);
    } else {
      shelfOccupied[i] = false;
      shelfFillPercent[i] = 0.0f;
    }
  }
}

void printShelfStatus() {
  Serial.println("╔══════════════════════════════════════════╗");
  Serial.println("║             貨架即時狀態                 ║");
  Serial.println("╚══════════════════════════════════════════╝");
  for (int i = 0; i < SHELF_COUNT; i++) {
    Serial.printf(" 第%2d格 | 深度%3.0fcm | 前%3ldcm 後%3ldcm → ", i+1, shelfDepth[i], distFront[i], distBack[i]);
    if (shelfOccupied[i]) {
      Serial.printf("有貨  %.1f%%\n", shelfFillPercent[i]);
    } else {
      Serial.printf("空棚\n");
    }
  }
  Serial.println("──────────────────────────────────────────");
}