// Host-side Wire stand-in: one I2C device answers at simI2cAddr.
#pragma once
#include "Arduino.h"
extern byte simI2cAddr;
struct SimWire {
  byte addr = 0;
  void begin() {}
  void beginTransmission(byte a) { addr = a; }
  byte endTransmission() { return addr == simI2cAddr ? 0 : 2; }
};
extern SimWire Wire;
