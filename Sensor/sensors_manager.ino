// ==================== sensors_manager.ino ====================
// 修正版：使用指標陣列，完美支援多顆 Grove Ultrasonic
// ===========================================================

#include "Ultrasonic.h"

// ------ 設定腳位與數量 ------
#define SENSOR_COUNT 2
const uint8_t sensorPins[SENSOR_COUNT] = {5, 7};   // 改這裡就行

// ------ 正確宣告：指標陣列 ------
Ultrasonic* ultrasonic[SENSOR_COUNT];   // 關鍵！用指標

// ------ 儲存距離 ------
long distances[SENSOR_COUNT] = {0};

// ------ 計時用 ------
unsigned long lastTriggerTime = 0;
const unsigned long TRIGGER_INTERVAL = 70;

// ===============================================================
void setupSensors() {
  for (int i = 0; i < SENSOR_COUNT; i++) {
    ultrasonic[i] = new Ultrasonic(sensorPins[i]);   // 動態建立
  }
  Serial.println("[Sensors] 多顆超聲波感測器初始化完成");
}

// ===============================================================
void ReadAllSensors() {
  static uint8_t currentSensor = 0;

  if (millis() - lastTriggerTime < TRIGGER_INTERVAL) return;
  lastTriggerTime = millis();

  long raw = ultrasonic[currentSensor]->MeasureInCentimeters();

  //根據 Grove - Ultrasonic 官方數據,偵測距離介於 2 ~ 400 cm
  if (raw < 2 || raw > 400) {
    distances[currentSensor] = -1;
  } else {
    distances[currentSensor] = raw;
  }

  currentSensor++;
  if (currentSensor >= SENSOR_COUNT) {
    currentSensor = 0;
  }
}

// ===============================================================
void printAllDistances() {
  Serial.print("[距離] ");
  for (int i = 0; i < SENSOR_COUNT; i++) {
    Serial.print("S");
    Serial.print(i + 1);
    Serial.print(": ");
    if (distances[i] == -1) Serial.print("--- ");
    else {
      Serial.print(distances[i]);
      Serial.print("cm ");
    }
    if (i < SENSOR_COUNT - 1) Serial.print(" | ");
  }
  Serial.println();
}