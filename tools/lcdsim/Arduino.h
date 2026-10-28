// Host-side Arduino stand-in for the LCD sketch: microsecond clock, Serial and F().
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>

typedef uint8_t byte;
typedef bool boolean;
#define F(s) (s)
#define HEX 16

extern unsigned long long simUs;
inline unsigned long millis() { return simUs / 1000; }
inline unsigned long micros() { return simUs; }
inline void delay(unsigned long) {}
inline void yield() {}
inline void noInterrupts() {}
inline void interrupts() {}

struct SimSerial {
  void begin(unsigned long) {}
  void print(const char *s) { printf("[serial] %s", s); }
  void print(int v, int) { printf("%X", v); }
  void println(const char *s) { printf("%s\n", s); }
};
extern SimSerial Serial;
