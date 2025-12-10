// ==================== shelf_config.ino ====================
// 所有貨架格子的設定：深度 + 前後感測器腳位
// 關鍵修正：改用指標陣列 + 動態建立物件
// ========================================================

#include "Ultrasonic.h"

// ---------- 設定總共有幾格 ----------
#define SHELF_COUNT 1       // 改成你實際格子數（最多20格都OK）

// ---------- 每格的實際深度（公分）----------
const float shelfDepth[SHELF_COUNT] = {
  27    // 第5、6格 不一樣也行！
};

// ---------- 每格的前後感測器腳位 ----------
const uint8_t pinFront[SHELF_COUNT] = {5};  // 前方
const uint8_t pinBack[SHELF_COUNT]  = {7};  // 後方

// ---------- 正確寫法：用指標陣列 ----------
Ultrasonic* sensorFront[SHELF_COUNT] = {nullptr};
Ultrasonic* sensorBack[SHELF_COUNT]  = {nullptr};

// ---------- 全域狀態變數 ----------
bool    shelfOccupied[SHELF_COUNT]    = {false};
float   shelfFillPercent[SHELF_COUNT] = {0.0};
long    distFront[SHELF_COUNT]        = {0};
long    distBack[SHELF_COUNT]         = {0};