/*
  valve_controller.ino  (demo-stable build)
  ---------------------------------------------------------------------------
  BCE497J - Deep Learning and IoT-Based Real-Time Variable-Rate Chemical
  Spraying System for Disease Control in Paddy Crop.

  Arduino Nano V3.0 (ATmega328P). Receives a spray command from the ESP32-CAM
  over SoftwareSerial and opens the relay-driven solenoid valve for the
  requested duration, then closes it.

  This build is deliberately simple and blocking, because it is the version
  that behaves reliably on the bench with the pump running. The spray is one
  unbroken sequence: drive the relay OPEN, wait the requested time, drive it
  CLOSED. The close always runs immediately after the open in the same
  function call, so the valve cannot be left open by a missed timer pass.

  SERIAL PROTOCOL (matches esp32cam_sprayer.ino)
  ------------------------------------------------
      S<ms>,<cat>\n           (plain, no checksum)
  or  S<ms>,<cat>*<HH>\n       (with the v2 checksum; the '*...' part is
                               simply ignored here, so either form works)

      <ms>  : integer, solenoid open time in milliseconds (0 = no spray).
      <cat> : integer 0-3, category code (logging only).

  Bench/dry-run (USB Serial Monitor, 9600 baud):
      0..3  test sprays (0 = no-op, 1 = 1.25 s, 2 = 1.875 s, 3 = 2.5 s)
      x     force the valve closed right now

  SAFETY
  ------
  * MAX_VALVE_OPEN_MS caps a single spray so a bad reading cannot empty the
    tank.
  * The relay is driven to CLOSED before the pin becomes an output, and again
    at the very start of setup(), so the valve is never left open across a
    reset.

  Pin usage:
    D10  SoftwareSerial RX  <- ESP32-CAM GPIO1 (TX)
    D11  SoftwareSerial TX  -> (unused, reserved)
    D7   Relay IN
    D13  Onboard LED, lit while the valve is open
*/

#include <SoftwareSerial.h>

#define RX_PIN              10   // from ESP32-CAM GPIO1 (TX)
#define TX_PIN              11   // reserved, unused
#define RELAY_PIN            7
#define STATUS_LED_PIN      13

#define SERIAL_BAUD_TO_ESP32 9600
#define MAX_VALVE_OPEN_MS   5000UL   // hardware_implementation_plan.md section 11

// Relay board polarity.
//   0 = ACTIVE-HIGH: relay energises (valve OPENS) when D7 is HIGH.
//   1 = ACTIVE-LOW : relay energises (valve OPENS) when D7 is LOW.
// This board was confirmed on the bench as active-HIGH (both relay LEDs lit
// = valve open when D7 is HIGH), so leave this at 0.
#define RELAY_ACTIVE_LOW      0

inline void relayWrite(bool open) {
  int level;
  if (RELAY_ACTIVE_LOW) {
    level = open ? LOW : HIGH;
  } else {
    level = open ? HIGH : LOW;
  }
  digitalWrite(RELAY_PIN, level);
}

#define QS_MLS_DESIGN          3.5   // design value, debug printout only

// Bench durations for digits 0..3.
const unsigned long TEST_DURATION_MS[4] = {0, 1250, 1875, 2500};

SoftwareSerial espLink(RX_PIN, TX_PIN);

char lineBuf[32];
uint8_t lineLen = 0;

// ---------------------------------------------------------------------------
// Valve control: one unbroken OPEN -> wait -> CLOSE sequence.
// ---------------------------------------------------------------------------
void spray(unsigned long ms, int categoryCode) {
  if (ms == 0) {
    Serial.println(F("[valve] ts=0 (Healthy), no spray"));
    return;
  }
  if (ms > MAX_VALVE_OPEN_MS) {
    Serial.print(F("[safety] "));
    Serial.print(ms);
    Serial.print(F(" ms exceeds cap, clamped to "));
    Serial.println(MAX_VALVE_OPEN_MS);
    ms = MAX_VALVE_OPEN_MS;
  }

  Serial.print(F("[valve] ON "));
  Serial.print(ms);
  Serial.print(F(" ms, cat "));
  Serial.print(categoryCode);
  Serial.print(F(", ~"));
  Serial.print(ms / 1000.0 * QS_MLS_DESIGN, 2);
  Serial.println(F(" mL at design Qs"));
  Serial.flush();

  // OPEN
  relayWrite(true);
  digitalWrite(STATUS_LED_PIN, HIGH);

  // Hold open for the requested time. Blocking on purpose: the close below
  // is guaranteed to run right after, in the same call, with nothing that can
  // skip it.
  delay(ms);

  // CLOSE
  relayWrite(false);
  digitalWrite(STATUS_LED_PIN, LOW);
  Serial.println(F("[valve] CLOSED"));
}

// Force closed immediately (bench 'x').
void forceClose() {
  relayWrite(false);
  digitalWrite(STATUS_LED_PIN, LOW);
  Serial.println(F("[valve] force CLOSED"));
}

// ---------------------------------------------------------------------------
// Parse "S<ms>,<cat>" (any trailing "*<HH>" checksum is ignored).
// ---------------------------------------------------------------------------
void handleLine(const char *line) {
  if (line[0] != 'S') return;   // ignore all ESP32 debug text

  // ms = digits after 'S' up to the comma.
  const char *p = line + 1;
  unsigned long ms = 0;
  uint8_t digits = 0;
  while (*p >= '0' && *p <= '9' && digits < 7) {
    ms = ms * 10UL + (unsigned long)(*p - '0');
    p++;
    digits++;
  }
  if (digits == 0 || *p != ',') {
    Serial.println(F("[link] S-line ignored (bad format)"));
    return;
  }
  p++;  // skip comma
  int cat = 0;
  if (*p >= '0' && *p <= '3') {
    cat = *p - '0';
  }
  spray(ms, cat);
}

void pollEspLink() {
  while (espLink.available()) {
    char c = (char)espLink.read();
    if (c == '\n') {
      if (lineLen > 0) {
        lineBuf[lineLen] = '\0';
        handleLine(lineBuf);
      }
      lineLen = 0;
    } else if (c != '\r') {
      if (lineLen < sizeof(lineBuf) - 1) {
        lineBuf[lineLen++] = c;
      } else {
        lineLen = 0;   // overflow, drop the line
      }
    }
  }
}

void pollBench() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == 'x' || c == 'X') {
      forceClose();
    } else if (c >= '0' && c <= '3') {
      int idx = c - '0';
      Serial.print(F("[bench] test "));
      Serial.println(idx);
      spray(TEST_DURATION_MS[idx], idx);
    }
  }
}

void setup() {
  // FAIL-SAFE: force the valve CLOSED the instant the board powers up or
  // resets, BEFORE anything else. If the pump browns out the Nano in the
  // middle of a spray, the board reboots straight into this, so the valve
  // can never be left stuck open by a reset. The relay is driven to its
  // closed level, then the pin is made an output, then driven closed again.
  relayWrite(false);
  pinMode(RELAY_PIN, OUTPUT);
  relayWrite(false);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  Serial.begin(SERIAL_BAUD_TO_ESP32);
  espLink.begin(SERIAL_BAUD_TO_ESP32);

  Serial.println();
  Serial.println(F("[boot] PaddyGuard valve controller ready (valve forced CLOSED on boot)"));
  Serial.println(F("[boot] bench: type 0, 1, 2 or 3 to dry-run; x to force close"));
}

void loop() {
  pollEspLink();
  pollBench();
}
