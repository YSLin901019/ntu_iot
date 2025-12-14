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
  const char* id;        // 貨架編號（例如："A1", "B2"）
  uint8_t pin;           // 感測器腳位
  bool enabled;          // 是否啟用（由使用者控制）
  float shelf_length;    // 貨架總長度（cm，透過校正獲得）
};

// 每格貨架的配置（編號 + 腳位 + 啟用狀態 + 貨架長度）
// enabled = true: 啟用，會進行掃描並回傳數據
// enabled = false: 停用，不會掃描，不會回傳數據
// shelf_length = 0.0: 尚未校正，> 0: 已校正的長度（cm）
ShelfConfig shelfConfig[SHELF_COUNT] = {
  {"A1", 4,  false, 0.0},   // 貨架 A1，GPIO 4
  {"A2", 5,  false, 0.0},   // 貨架 A2，GPIO 5
  {"A3", 6,  false, 0.0},   // 貨架 A3，GPIO 6
  {"A4", 7,  false, 0.0},   // 貨架 A4，GPIO 7
  {"B1", 8,  false, 0.0},   // 貨架 B1，GPIO 8
  {"B2", 9,  false, 0.0},   // 貨架 B2，GPIO 9
  {"B3", 10, false, 0.0},   // 貨架 B3，GPIO 10
  {"B4", 11, false, 0.0},   // 貨架 B4，GPIO 11
  {"C1", 12, false, 0.0},   // 貨架 C1，GPIO 12
  {"C2", 13, false, 0.0},   // 貨架 C2，GPIO 13
  {"C3", 14, false, 0.0},   // 貨架 C3，GPIO 14
  {"C4", 15, false, 0.0}    // 貨架 C4，GPIO 15
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

