// Host-side Arduino stand-in for finger_led.ino: Serial with an input queue and a pin array.
#pragma once
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

typedef unsigned char byte;
#define OUTPUT 1

extern int simPin[20];
inline void pinMode(int, int) {}
inline void analogWrite(int pin, int v) { simPin[pin] = v; }

struct SimSerial {
  std::string in, out;
  void begin(long) {}
  int available() { return (int)in.size(); }
  int read() {
    int c = (unsigned char)in[0];
    in.erase(0, 1);
    return c;
  }
  void print(const char *v) { out += v; }
  void println(const char *v) { out += v; out += "\r\n"; }
  void println(int v) { out += std::to_string(v) + "\r\n"; }
};
extern SimSerial Serial;
