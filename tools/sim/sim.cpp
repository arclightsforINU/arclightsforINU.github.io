// Runs an Arduino sketch on a simulated millisecond clock and checks or prints its LED timing.
#include "Arduino.h"
#include <vector>
#include <sys/wait.h>
#include <unistd.h>

unsigned long simNow = 0;
int simPot = 0;
SimSerial Serial;

struct Event { unsigned long t; int pin; int value; };
std::vector<Event> events;
int pinState[20];

void simWrite(uint8_t pin, uint8_t value) {
  if (pinState[pin] == value) return;
  pinState[pin] = value;
  events.push_back({simNow, pin, value});
}

#include SKETCH

void runUntil(unsigned long end) {
  for (; simNow < end; simNow++)
    for (int i = 0; i < 4; i++) loop();
}

#ifdef TRACE
int main() {
  setup();
  runUntil(TRACE);
  for (const Event &e : events) printf("%5lu ms  D%-2d %s\n", e.t, e.pin, e.value ? "ON" : "off");
}
#else
struct Step { unsigned long at; int pot; };

int potAt(const std::vector<Step> &plan, unsigned long t) {
  int pot = plan[0].pot;
  for (const Step &s : plan) if (s.at <= t) pot = s.pot;
  return pot;
}

bool check(const char *name, std::vector<Step> plan, unsigned long end) {
  events.clear();
  for (int &p : pinState) p = LOW;
  simNow = 0;
  simPot = plan[0].pot;
  size_t next = 1;
  setup();
  while (simNow < end) {
    if (next < plan.size() && simNow == plan[next].at) simPot = plan[next++].pot;
    runUntil(simNow + 1);
  }

  std::vector<Event> want;
  std::vector<unsigned long> periods;
  for (unsigned long s = events.empty() ? 0 : events[0].t; ; ) {
    unsigned long p = map(potAt(plan, s), 0, 1023, 500, 3000);
    unsigned long off = s + p * 3 / 5;
    if (off >= end) break;
    want.push_back({s, 13, HIGH});
    want.push_back({s + p / 10, 10, HIGH});
    want.push_back({s + p / 5, 7, HIGH});
    want.push_back({off, 13, LOW});
    want.push_back({off, 10, LOW});
    want.push_back({off, 7, LOW});
    periods.push_back(p);
    s += p;
  }
  while (events.size() > want.size()) events.pop_back();

  bool ok = events.size() == want.size();
  for (size_t i = 0; ok && i < want.size(); i++)
    ok = events[i].t == want[i].t && events[i].pin == want[i].pin && events[i].value == want[i].value;

  printf("%-34s %s  cycles=%zu  periods(ms):", name, ok ? "PASS" : "FAIL", periods.size());
  for (size_t i = 0; i < periods.size() && i < 6; i++) printf(" %lu", periods[i]);
  printf("\n");
  if (!ok)
    for (size_t i = 0; i < events.size() || i < want.size(); i++)
      printf("  #%zu got %lu D%d=%d | want %lu D%d=%d\n", i,
             i < events.size() ? events[i].t : 0, i < events.size() ? events[i].pin : 0, i < events.size() ? events[i].value : 0,
             i < want.size() ? want[i].t : 0, i < want.size() ? want[i].pin : 0, i < want.size() ? want[i].value : 0);
  return ok;
}

bool isolated(const char *name, std::vector<Step> plan, unsigned long end) {
  fflush(stdout);
  pid_t pid = fork();
  if (pid == 0) {
    bool ok = check(name, plan, end);
    fflush(stdout);
    _exit(ok ? 0 : 1);
  }
  int status = 0;
  waitpid(pid, &status, 0);
  return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

int main() {
  bool ok = true;
  ok &= isolated("pot 0 (min) -> 500 ms", {{0, 0}}, 5000);
  ok &= isolated("pot 1023 (max) -> 3000 ms", {{0, 1023}}, 15000);
  ok &= isolated("pot 512 (mid) -> 1751 ms", {{0, 512}}, 9000);
  ok &= isolated("pot 204 -> 998 ms", {{0, 204}}, 6000);
  ok &= isolated("turned mid-cycle 0 -> 1023 @1200", {{0, 0}, {1200, 1023}}, 9000);
  ok &= isolated("turned mid-cycle 1023 -> 0 @4000", {{0, 1023}, {4000, 0}}, 9000);
  printf("%s\n", ok ? "ALL PASS" : "SOME FAILED");
  return ok ? 0 : 1;
}
#endif
