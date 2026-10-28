// Host-side Arduino stand-in: simulated clock, pins and potentiometer for timing tests.
#pragma once
#include <cstdint>
#include <cstdio>

typedef uint8_t byte;
typedef bool boolean;
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define A0 14

extern unsigned long simNow;
extern int simPot;
void simWrite(uint8_t pin, uint8_t value);

inline unsigned long millis() { return simNow; }
inline unsigned long micros() { return simNow * 1000UL; }
inline void delay(unsigned long) {}
inline void yield() {}
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t pin, uint8_t value) { simWrite(pin, value); }
inline int analogRead(uint8_t) { return simPot; }
inline long map(long x, long in_min, long in_max, long out_min, long out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}
inline void noInterrupts() {}
inline void interrupts() {}

struct SimSerial {
  void begin(unsigned long) {}
  void println(unsigned long) {}
};
extern SimSerial Serial;
