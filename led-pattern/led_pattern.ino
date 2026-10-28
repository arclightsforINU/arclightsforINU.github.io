const int ledPins[] = {2, 3, 4, 5};
const int ledCount = 4;

void setup() {
  for (int led = 0; led < ledCount; led++) {
    pinMode(ledPins[led], OUTPUT);
  }
}

void loop() {
  for (int count = 1; count <= 3; count++) {
    for (int start = 0; start < ledCount; start++) {
      for (int led = 0; led < ledCount; led++) {
        digitalWrite(ledPins[led], led >= start && led < start + count ? HIGH : LOW);
      }
      delay(500);
    }
  }
}
