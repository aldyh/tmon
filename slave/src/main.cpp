/*
 * tmon slave firmware -- ESP32-S3 blink test
 *
 * Minimal sketch to verify the toolchain and flash process.
 * Prints to serial so we can verify via 'make monitor-slave'.
 *
 * To monitor serial output manually:
 *   screen /dev/ttyACM0 115200
 */

#include <Arduino.h>

static int count = 0;

void
setup (void)
{
  Serial.begin (115200);
  pinMode (LED_BUILTIN, OUTPUT);
  Serial.println ("tmon slave blink test starting");
}

void
loop (void)
{
  digitalWrite (LED_BUILTIN, HIGH);
  Serial.print ("blink ");
  Serial.println (count++);
  delay (1000);
  digitalWrite (LED_BUILTIN, LOW);
  delay (1000);
}
