#include <TaskScheduler.h>

const byte LED[] = {13, 10, 7};
const byte POT = A0;

Scheduler runner;

void startCycle();
void onLED2() { digitalWrite(LED[1], HIGH); }
void onLED3() { digitalWrite(LED[2], HIGH); }
void offLEDs() { for (byte pin : LED) digitalWrite(pin, LOW); }

Task t1(1000, TASK_FOREVER, &startCycle, &runner, true);
Task t2(TASK_IMMEDIATE, TASK_ONCE, &onLED2, &runner);
Task t3(TASK_IMMEDIATE, TASK_ONCE, &onLED3, &runner);
Task t4(TASK_IMMEDIATE, TASK_ONCE, &offLEDs, &runner);

void startCycle() {
  unsigned long period = map(analogRead(POT), 0, 1023, 500, 3000);
  t1.setInterval(period);
  digitalWrite(LED[0], HIGH);
  t2.restartDelayed(period / 10);
  t3.restartDelayed(period / 5);
  t4.restartDelayed(period * 3 / 5);
  Serial.println(period);
}

void setup() {
  Serial.begin(115200);
  for (byte pin : LED) pinMode(pin, OUTPUT);
}

void loop() {
  runner.execute();
}
