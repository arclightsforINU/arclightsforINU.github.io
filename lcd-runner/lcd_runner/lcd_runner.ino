// Shows a running figure in the LCD's first cell for as long as the Arduino keeps running.
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <TaskScheduler.h>

const byte LCD_ADDR = 0x27;
const unsigned long START_MS = 320, FRAME_MS = 120, SPEEDUP_MS = 20;

byte POSES[4][8] = {
  {0b00011, 0b00011, 0b00100, 0b01110, 0b10101, 0b00110, 0b01001, 0b10000},
  {0b00000, 0b00011, 0b00011, 0b00100, 0b01110, 0b10100, 0b01100, 0b00100},
  {0b00011, 0b00011, 0b00100, 0b00110, 0b01100, 0b00110, 0b00100, 0b00100},
  {0b00011, 0b00011, 0b00100, 0b01111, 0b10100, 0b00111, 0b01000, 0b10000},
};

LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
Scheduler runner;
byte pose = 0;
unsigned long steps = 0;

void nextPose();
Task tPose(START_MS, TASK_FOREVER, &nextPose, &runner, true);

void showStatus() {
  unsigned long s = millis() / 1000;
  char line[15];
  snprintf(line, sizeof line, "RUN %02lu:%02lu:%02lu", s / 3600, s / 60 % 60, s % 60);
  lcd.setCursor(2, 0);
  lcd.print(line);
  snprintf(line, sizeof line, "%lu steps", steps);
  lcd.setCursor(2, 1);
  lcd.print(line);
}

void nextPose() {
  if (tPose.getInterval() > FRAME_MS) tPose.setInterval(tPose.getInterval() - SPEEDUP_MS);
  lcd.setCursor(0, 0);
  lcd.write(pose);
  pose = (pose + 1) % 4;
  if (pose == 0) {
    steps++;
    showStatus();
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.beginTransmission(LCD_ADDR);
  if (Wire.endTransmission() != 0) {
    for (byte a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        Serial.print(F("LCD_ADDR을 0x"));
        Serial.print(a, HEX);
        Serial.println(F("로 바꾸세요"));
      }
    }
  }
  lcd.init();
  lcd.backlight();
  for (byte i = 0; i < 4; i++) lcd.createChar(i, POSES[i]);
  lcd.clear();
  showStatus();
}

void loop() { runner.execute(); }
