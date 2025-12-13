// ==================== shelf_config.ino ====================
// 貨架配置檔案：格數、感測器腳位、啟用狀態
// 說明：ESP32 只收集啟用貨架的感測器數據並發送到 RPI
// =========================================================

// ---------- 可用的 GPIO 腳位 ----------
// GPIO 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
// 共 12 個可用腳位，最多支援 12 個貨架

// ---------- 設定總共有幾格 ----------
#define SHELF_COUNT 12       // 改成你實際的貨架格數（最多12個）

// ---------- 貨架配置定義 ----------
struct ShelfConfig {
  const char* id;    // 貨架編號（例如："A1", "B2"）
  uint8_t pin;       // 感測器腳位
  bool enabled;      // 是否啟用（只有啟用的貨架才會掃描）
};

// 每格貨架的配置（編號 + 腳位 + 啟用狀態）
// enabled = true: 啟用，會進行掃描並回傳數據
// enabled = false: 停用，不會掃描，不會回傳數據
ShelfConfig shelfConfig[SHELF_COUNT] = {
  {"A1", 4,  true},   // 貨架 A1，GPIO 4，啟用
  {"A2", 5,  true},   // 貨架 A2，GPIO 5，啟用
  {"A3", 6,  false},  // 貨架 A3，GPIO 6，停用
  {"A4", 7,  false},  // 貨架 A4，GPIO 7，停用
  {"B1", 8,  false},  // 貨架 B1，GPIO 8，停用
  {"B2", 9,  false},  // 貨架 B2，GPIO 9，停用
  {"B3", 10, false},  // 貨架 B3，GPIO 10，停用
  {"B4", 11, false},  // 貨架 B4，GPIO 11，停用
  {"C1", 12, false},  // 貨架 C1，GPIO 12，停用
  {"C2", 13, false},  // 貨架 C2，GPIO 13，停用
  {"C3", 14, false},  // 貨架 C3，GPIO 14，停用
  {"C4", 15, false}   // 貨架 C4，GPIO 15，停用
};

// ---------- 感測器物件（使用指標陣列）----------
Ultrasonic* sensors[SHELF_COUNT] = {nullptr};

// ---------- 即時感測器讀值 ----------
long distance[SHELF_COUNT] = {0};  // 距離（毫米）

// ---------- 取得啟用的貨架數量 ----------
int getEnabledShelfCount() {
  int count = 0;
  for (int i = 0; i < SHELF_COUNT; i++) {
    if (shelfConfig[i].enabled) {
      count++;
    }
  }
  return count;
}

