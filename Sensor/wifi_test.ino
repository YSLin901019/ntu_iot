#include <Wifi.h>


#define wifi_ssid "iPhone"
#define wifi_password "5603901019"



void setup() {
  Serial.begin(115200);
  WiFi.begin(wifi_ssid, wifi_password);
  Serial.println("starting wifi connection.");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED){
    Serial.println("Connected");
  }
}