/*
 * tmon slave firmware -- ESP32-S3 blink test
 *
 * Minimal sketch to verify the toolchain and flash process.
 */

#include <Arduino.h>

#define LED_PIN 2

void
setup (void)
{
  pinMode (LED_PIN, OUTPUT);
}

void
loop (void)
{
  digitalWrite (LED_PIN, HIGH);
  delay (500);
  digitalWrite (LED_PIN, LOW);
  delay (500);
}
