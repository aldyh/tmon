/*
 * led.cpp -- Status LED driver for tmon client (ESP32-S3)
 *
 * Uses the built-in WS2812 RGB LED on GPIO 48 to signal state.
 * All blink functions are blocking (delay() yields to the RTOS).
 * The LED is off between calls.
 */

#include "led.h"

#include <Adafruit_NeoPixel.h>

/* GPIO for built-in WS2812 LED on ESP32-S3-DevKitC-1 */
static const int LED_PIN = 48;
static const int NUM_LEDS = 1;

/* Blink interval (ms) -- on time and off time for each blink */
static const uint32_t BLINK_INTERVAL = 300;

/* LED brightness (0-255) */
static const uint8_t BRIGHTNESS = 20;

/* Colors */
static const uint32_t COLOR_OFF    = 0x000000;
static const uint32_t COLOR_RED    = 0xFF0000;
static const uint32_t COLOR_GREEN  = 0x00FF00;
static const uint32_t COLOR_YELLOW = 0xFFFF00;

static Adafruit_NeoPixel led (NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

/*
 * Set LED to a solid color.
 */
static void
led_set_color (uint32_t color)
{
  led.setPixelColor (0, color);
  led.show ();
}

/*
 * Blink the LED count times in the given color, then turn off.
 * Blocks for count * BLINK_INTERVAL * 2 milliseconds.
 */
static void
led_blink (uint32_t color, uint8_t count)
{
  for (uint8_t i = 0; i < count; i++)
    {
      led_set_color (color);
      delay (BLINK_INTERVAL);
      led_set_color (COLOR_OFF);
      delay (BLINK_INTERVAL);
    }
}

/*
 * Initialize the status LED subsystem.
 */
void
led_init (void)
{
  led.begin ();
  led.setBrightness (BRIGHTNESS);
  led_set_color (COLOR_OFF);
}

/*
 * Blink yellow count times (blocking).
 */
void
led_identify (uint8_t count)
{
  led_blink (COLOR_YELLOW, count);
}

/*
 * Blink red count times (blocking).
 */
void
led_error_blink (uint8_t count)
{
  led_blink (COLOR_RED, count);
}

/*
 * Blink green once after transmitting a reading (blocking).
 */
void
led_tx_blink (void)
{
  led_blink (COLOR_GREEN, 1);
}
