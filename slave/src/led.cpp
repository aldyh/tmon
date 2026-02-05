/*
 * led.cpp -- Status LED driver for tmon slave (ESP32-S3)
 *
 * Uses the built-in WS2812 RGB LED on GPIO 48 to signal state.
 * See led.h for state descriptions.
 */

#include "led.h"

#include <Adafruit_NeoPixel.h>

/* GPIO for built-in WS2812 LED on ESP32-S3-DevKitC-1 */
static const int LED_PIN = 48;
static const int NUM_LEDS = 1;

/* TX blink duration (ms) */
static const uint32_t TX_BLINK_DURATION = 100;

/* LED brightness (0-255) */
static const uint8_t BRIGHTNESS = 20;

/* Colors */
static const uint32_t COLOR_OFF   = 0x000000;
static const uint32_t COLOR_GREEN = 0x00FF00;
static const uint32_t COLOR_RED   = 0xFF0000;

/* LED states */
typedef enum
{
  LED_OFF,    /* LED off (normal) */
  LED_ERROR,  /* Solid red */
  LED_TX      /* Blinking green (auto-returns to previous) */
} led_state_t;

/* Internal state */
static Adafruit_NeoPixel led (NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
static led_state_t current_state = LED_OFF;
static led_state_t state_before_tx = LED_OFF;
static uint32_t watchdog_timeout = 0;
static uint32_t last_tx_time = 0;
static uint32_t tx_blink_start = 0;
static int ever_transmitted = 0;

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
 * timeout_ms: watchdog timeout; LED turns red if no TX within this period.
 *             Set to 0 to disable watchdog.
 */
void
led_init (uint32_t timeout_ms)
{
  watchdog_timeout = timeout_ms;
  current_state = LED_OFF;
  state_before_tx = LED_OFF;
  last_tx_time = 0;
  tx_blink_start = 0;
  ever_transmitted = 0;

  led.begin ();
  led.setBrightness (BRIGHTNESS);
  led_set_color (COLOR_OFF);
}

/*
 * Set error state (solid red).
 * Error state persists until reset.
 */
void
led_error (void)
{
  current_state = LED_ERROR;
  state_before_tx = LED_ERROR;
  led_set_color (COLOR_RED);
}

/*
 * Trigger brief green blink for transmission.
 * Resets watchdog timer.
 */
void
led_blink (void)
{
  /* Save current state to return to after blink */
  if (current_state != LED_TX)
    state_before_tx = current_state;

  current_state = LED_TX;
  tx_blink_start = 0;  /* Will be set on next update */
  led_set_color (COLOR_GREEN);
}

/*
 * Update LED state machine and output.
 * now_ms: current time in milliseconds.
 * Call every loop iteration. Non-blocking.
 */
void
led_update (uint32_t now_ms)
{
  /* Record TX time if blink just started */
  if (current_state == LED_TX && tx_blink_start == 0)
    {
      tx_blink_start = now_ms;
      last_tx_time = now_ms;
      ever_transmitted = 1;
    }

  /* Handle TX blink timeout */
  if (current_state == LED_TX)
    {
      if ((now_ms - tx_blink_start) >= TX_BLINK_DURATION)
        {
          /* Return to previous state */
          current_state = state_before_tx;
          if (current_state == LED_ERROR)
            led_set_color (COLOR_RED);
          else
            led_set_color (COLOR_OFF);
        }
      return;
    }

  /* Check watchdog timeout (only if enabled and we've transmitted before) */
  if (watchdog_timeout > 0 && ever_transmitted)
    {
      if ((now_ms - last_tx_time) >= watchdog_timeout)
        led_error ();
    }
}
