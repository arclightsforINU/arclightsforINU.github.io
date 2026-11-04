// Sets the brightness of the LED on D9 from "LEVEL:<0-255>" lines sent by the p5 page.
//
// The level is perceived brightness, not PWM duty. The eye is far more sensitive to changes
// in dim light than in bright light, so a linear duty makes the bottom of the slider jump and
// the top barely change. The CIE 1931 lightness formula converts the level to duty instead,
// so equal finger movements look like equal steps of brightness.
//
// Replies (9600 baud, one line each):
//   READY            after reset; the board resets whenever the port is opened
//   PWM:<duty>       the duty actually written for a valid LEVEL line
//   ERR:<reason>     the line was ignored

const byte LED_PIN = 9;           // PWM-capable pin (~)
const byte MAX_LINE_LENGTH = 15;  // "LEVEL:255" is 9 characters

char line[MAX_LINE_LENGTH + 1];
byte lineLength = 0;
bool lineTooLong = false;

byte dutyForLevel(byte level) {
  float lightness = level * 100.0 / 255.0;                    // CIE L*, 0-100
  float luminance = lightness <= 8.0 ? lightness / 903.3      // linear segment near black
                                     : pow((lightness + 16.0) / 116.0, 3);
  return (byte)(luminance * 255.0 + 0.5);
}

// Accepts exactly "LEVEL:" followed by 1-3 digits with a value of at most 255.
bool parseLevel(const char *text, byte *level) {
  const char *digits = text + 6;
  if (strncmp(text, "LEVEL:", 6) != 0 || !isdigit(digits[0])) return false;
  char *end;
  long value = strtol(digits, &end, 10);
  if (*end != '\0' || end - digits > 3 || value > 255) return false;
  *level = value;
  return true;
}

void handleLine() {
  byte level;
  if (!parseLevel(line, &level)) {
    Serial.print("ERR:");
    Serial.println(line);
    return;
  }
  byte duty = dutyForLevel(level);
  analogWrite(LED_PIN, duty);
  Serial.print("PWM:");
  Serial.println(duty);
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  analogWrite(LED_PIN, 0);
  Serial.begin(9600);
  Serial.println("READY");
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c != '\n') {
      if (lineLength < MAX_LINE_LENGTH) line[lineLength++] = c;
      else lineTooLong = true;
      continue;
    }
    line[lineLength] = '\0';
    if (lineTooLong) Serial.println("ERR:too long");
    else if (lineLength > 0) handleLine();
    lineLength = 0;
    lineTooLong = false;
  }
}
