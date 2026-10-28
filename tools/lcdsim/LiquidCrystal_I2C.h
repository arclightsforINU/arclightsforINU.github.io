// Host-side HD44780 model behind the LiquidCrystal_I2C API: DDRAM, CGRAM, the shared address counter and I2C time per byte.
#pragma once
#include "Arduino.h"

const unsigned long LCD_BYTE_US = 1480;
extern unsigned long long simInitUs;

struct LiquidCrystal_I2C {
  byte addr, cols, rows;
  byte ddram[2][40];
  byte cgram[8][8];
  bool inCgram = false;
  int ac = 0;
  unsigned long writes = 0;
  LiquidCrystal_I2C(byte a, byte c, byte r) : addr(a), cols(c), rows(r) { memset(ddram, ' ', sizeof ddram); memset(cgram, 0, sizeof cgram); }
  void init() { simUs += simInitUs; }
  void backlight() {}
  void clear() { memset(ddram, ' ', sizeof ddram); inCgram = false; ac = 0; simUs += LCD_BYTE_US + 2000; }
  void setCursor(byte c, byte r) { inCgram = false; ac = r * 40 + c; simUs += LCD_BYTE_US; }
  void createChar(byte loc, byte map[]) {
    for (int i = 0; i < 8; i++) cgram[loc & 7][i] = map[i];
    inCgram = true;
    ac = (loc & 7) * 8 + 8;
    simUs += 9 * LCD_BYTE_US;
  }
  size_t write(byte v) {
    writes++;
    simUs += LCD_BYTE_US;
    if (inCgram) { cgram[(ac / 8) & 7][ac % 8] = v; ac = (ac + 1) % 64; }
    else { ddram[ac / 40][ac % 40] = v; ac = (ac + 1) % 80; }
    return 1;
  }
  size_t print(const char *s) { size_t n = 0; while (*s) n += write((byte)*s++); return n; }
};
