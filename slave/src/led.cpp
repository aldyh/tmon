/*
 * led.cpp -- Status LED driver for tmon slave (ESP32-S3)
 *
 * Uses the built-in WS2812 RGB LED on GPIO 48 to signal state.
 * Two states: OFF (normal) and ERROR (blinking red, 500ms on/off).
 */

#include "led.h"

#include <Adafruit_NeoPixel.h>

/* GPIO for built-in WS2812 LED on ESP32-S3-DevKitC-1 */
static const int LED_PIN = 48;
static const int NUM_LEDS = 1;

/* Blink interval for error state (ms) */
static const uint32_t BLINK_INTERVAL = 500;

/* LED brightness (0-255) */
static const uint8_t BRIGHTNESS = 20;

/* Colors */
static const uint32_t COLOR_OFF = 0x000000;
static const uint32_t COLOR_RED = 0xFF0000;

/* LED states */
typedef enum
{
  LED_OFF,
  LED_ERROR
} led_state_t;

/* Internal state */
static Adafruit_NeoPixel led (NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
static led_state_t current_state = LED_OFF;
static uint32_t last_toggle_ms = 0;
static int led_on = 0;

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
 * Initialize the status LED subsystem.
 */
void
led_init (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;

  led.begin ();
  led.setBrightness (BRIGHTNESS);
  led_set_color (COLOR_OFF);
}

/*
 * Enter error state (blinking red).
 */
void
led_error (void)
{
  current_state = LED_ERROR;
  last_toggle_ms = 0;
  led_on = 1;
  led_set_color (COLOR_RED);
}

/*
 * Clear error and turn LED off.
 */
void
led_clear (void)
{
  current_state = LED_OFF;
  led_on = 0;
  led_set_color (COLOR_OFF);
}

/*
 * Drive blink animation.  Call every loop iteration.
 */
void
led_update (uint32_t now_ms)
{
  if (current_state != LED_ERROR)
    return;

  if (last_toggle_ms == 0)
    {
      last_toggle_ms = now_ms;
      return;
    }

  if ((now_ms - last_toggle_ms) >= BLINK_INTERVAL)
    {
      led_on = !led_on;
      led_set_color (led_on ? COLOR_RED : COLOR_OFF);
      last_toggle_ms = now_ms;
    }
}
