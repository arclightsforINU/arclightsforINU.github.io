// Feeds serial lines to finger_led.ino on the host and checks D9 and the replies.
// Build from the project root:
//   clang++ -std=c++17 -I arduino-lab/tools/fingersim arduino-lab/tools/fingersim/ino_test.cpp -o _build/finger_ino_check
#include "Arduino.h"

int simPin[20];
SimSerial Serial;

#include "../../finger-led/finger_led/finger_led.ino"

bool expect(const char *name, bool ok) {
  printf("%-56s %s\n", name, ok ? "PASS" : "FAIL");
  return ok;
}

// Delivers text, running loop() after each chunk as the board would between bytes.
std::string send(std::initializer_list<const char *> chunks) {
  Serial.out.clear();
  for (const char *chunk : chunks) {
    Serial.in += chunk;
    loop();
  }
  return Serial.out;
}

int reference(int level) {
  double l = level * 100.0 / 255.0;
  double y = l <= 8.0 ? l / 903.3 : std::pow((l + 16.0) / 116.0, 3);
  return (int)std::lround(y * 255.0);
}

int main() {
  bool ok = true;
  setup();
  ok &= expect("setup: D9 at 0, prints READY", simPin[9] == 0 && Serial.out == "READY\r\n");

  ok &= expect("LEVEL:255 -> duty 255, reply PWM:255", send({"LEVEL:255\n"}) == "PWM:255\r\n" && simPin[9] == 255);
  ok &= expect("LEVEL:0 -> duty 0", send({"LEVEL:0\n"}) == "PWM:0\r\n" && simPin[9] == 0);
  ok &= expect("LEVEL:128 -> duty 47 (CIE L* 50)", send({"LEVEL:128\n"}) == "PWM:47\r\n" && simPin[9] == 47);

  bool match = true, monotonic = true;
  int previous = -1;
  for (int level = 0; level <= 255; level++) {
    int duty = dutyForLevel(level);
    match &= duty == reference(level);
    monotonic &= duty >= previous;
    previous = duty;
  }
  ok &= expect("all 256 levels match the CIE formula", match);
  ok &= expect("duty never decreases as level rises", monotonic);

  ok &= expect("CRLF line accepted", send({"LEVEL:200\r\n"}) == "PWM:" + std::to_string(reference(200)) + "\r\n");
  ok &= expect("line split across reads is joined", send({"LEV", "EL:6", "4\n"}) == "PWM:" + std::to_string(reference(64)) + "\r\n");
  ok &= expect("two lines in one read both applied",
               send({"LEVEL:10\nLEVEL:255\n"}) == "PWM:" + std::to_string(reference(10)) + "\r\nPWM:255\r\n");

  int before = simPin[9];
  const char *bad[] = {"LEVEL:256\n", "LEVEL:\n", "LEVEL:12a\n", "LEVEL:-1\n", "LEVEL: 5\n", "LEVEL:0255\n", "level:5\n", "PWM:100\n"};
  bool rejected = true;
  for (const char *line : bad) rejected &= send({line}).rfind("ERR:", 0) == 0 && simPin[9] == before;
  ok &= expect("malformed or out-of-range lines -> ERR, D9 unchanged", rejected);

  ok &= expect("over-long line -> ERR:too long",
               send({"LEVEL:1234567890123456789\n"}) == "ERR:too long\r\n" && simPin[9] == before);
  ok &= expect("next line after an over-long one is clean", send({"LEVEL:255\n"}) == "PWM:255\r\n");
  ok &= expect("empty line -> no reply", send({"\n", "\r\n"}).empty());

  puts(ok ? "ALL PASS" : "SOME FAILED");
  return ok ? 0 : 1;
}
