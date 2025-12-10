void setup() {
  Serial.begin(115200);
  delay(500);
  setupWiFi();
  // 重要！這裡會建立所有感測器   
  setupShelf();  

  Serial.println("貨架管理者已啟動！");
}

void loop() {
  handleWiFiConnection();   // 一定要放這裡！持續重試
  updateShelfSensors();     // 你的貨架偵測

  // 例如每 30 秒印一次網路狀態
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 30000) {
    lastPrint = millis();
    printWiFiStatus();      // 隨時呼叫都行
  }

  if (millis() - lastPrint > 1000) {
    lastPrint = millis();
    printShelfStatus();
    printWiFiStatus();
  }
}