// Runs the LCD runner sketch on a simulated microsecond clock and checks what the display shows over time.
#include "Arduino.h"
#include "Wire.h"
#include "LiquidCrystal_I2C.h"
#include <string>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>

unsigned long long simUs = 0, simInitUs = 0;
byte simI2cAddr = 0x27;
SimSerial Serial;
SimWire Wire;

#include SKETCH

struct Change { unsigned long long t; byte code; };
std::vector<Change> firstCell;
std::string shownRow0, shownRow1;
unsigned long stepsWhenShown = 0, secondsWhenShown = 0;

std::string row(int r) {
  std::string s;
  for (int c = 0; c < 16; c++) s += lcd.ddram[r][c] < 8 ? '@' : (char)lcd.ddram[r][c];
  return s;
}

void run(unsigned long long endUs) {
  while (simUs < endUs) {
    unsigned long long before = simUs;
    loop();
    byte code = lcd.ddram[0][0];
    if (firstCell.empty() || firstCell.back().code != code) firstCell.push_back({before, code});
    if (row(0) != shownRow0) { shownRow0 = row(0); secondsWhenShown = before / 1000000; }
    if (row(1) != shownRow1) { shownRow1 = row(1); stepsWhenShown = steps; }
    simUs += 10;
  }
}

std::string pad16(std::string s) { return s + std::string(16 - s.size(), ' '); }

bool expect(const char *name, bool ok) {
  printf("%-48s %s\n", name, ok ? "PASS" : "FAIL");
  return ok;
}

bool check(bool verbose) {
  setup();
  bool glyphsAfterSetup = memcmp(lcd.cgram, POSES, sizeof POSES) == 0;
  run(65500000ULL);

  bool order = true;
  for (size_t i = 0; i < firstCell.size(); i++) order &= firstCell[i].code == i % 4;
  std::vector<double> gaps;
  for (size_t i = 1; i < firstCell.size(); i++) gaps.push_back((firstCell[i].t - firstCell[i - 1].t) / 1000.0);
  size_t warm = 0;
  bool warmup = true;
  for (; warm < gaps.size() && START_MS > SPEEDUP_MS * (warm + 1) + FRAME_MS; warm++)
    warmup &= std::abs(gaps[warm] - (double)(START_MS - SPEEDUP_MS * (warm + 1))) <= 2;
  double worst = 0;
  for (size_t i = warm; i < gaps.size(); i++) worst = std::max(worst, std::abs(gaps[i] - (double)FRAME_MS));

  char clock[17];
  snprintf(clock, sizeof clock, "@ RUN %02lu:%02lu:%02lu", secondsWhenShown / 3600, secondsWhenShown / 60 % 60, secondsWhenShown % 60);

  bool results[] = {
    glyphsAfterSetup && memcmp(lcd.cgram, POSES, sizeof POSES) == 0,
    order,
    warmup,
    worst <= 2,
    steps == firstCell.size() / 4,
    shownRow0 == pad16(clock),
    shownRow1 == pad16("  " + std::to_string(stepsWhenShown) + " steps"),
  };
  const char *names[] = {
    "CGRAM 0-3 hold the four poses",
    "first cell cycles 0,1,2,3,0,...",
    "warm-up gaps shrink by SPEEDUP_MS to FRAME_MS",
    "steady gaps stay within FRAME_MS +-2 ms",
    "steps = completed 4-pose cycles",
    "row 0 shows uptime at update time",
    "row 1 shows the step count at update time",
  };
  bool ok = true;
  for (size_t i = 0; i < 7; i++) {
    ok &= results[i];
    if (verbose || !results[i]) printf("  %-48s %s\n", names[i], results[i] ? "PASS" : "FAIL");
  }
  printf("  init %3llu ms: frames %zu, worst steady deviation %5.1f ms, gaps:", simInitUs / 1000, firstCell.size(), worst);
  for (size_t i = 0; i < 11 && i < gaps.size(); i++) printf(" %.0f", gaps[i]);
  printf("\n");
  if (verbose) printf("  row0 [%s]\n  row1 [%s]\n", row(0).c_str(), row(1).c_str());
  return ok;
}

bool isolated(unsigned long long initUs, bool verbose) {
  fflush(stdout);
  pid_t pid = fork();
  if (pid == 0) {
    simInitUs = initUs;
    bool ok = check(verbose);
    fflush(stdout);
    _exit(ok ? 0 : 1);
  }
  int status = 0;
  waitpid(pid, &status, 0);
  return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

int main() {
  int passed = 0;
  for (int ms = 0; ms < 120; ms += 10) passed += isolated(ms * 1000ULL, ms == 0);
  printf("%d/12 start-up offsets pass\n%s\n", passed, passed == 12 ? "ALL PASS" : "SOME FAILED");
  return passed == 12 ? 0 : 1;
}
