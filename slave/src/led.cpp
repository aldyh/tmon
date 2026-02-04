/*
 * led.cpp -- Status LED driver for tmon slave (ESP32-S3)
 *
 * Uses the built-in WS2812 RGB LED on GPIO 48 to signal connection state.
 * See led.h for state descriptions.
 */

#include "led.h"

#include <Adafruit_NeoPixel.h>

/* GPIO for built-in WS2812 LED on ESP32-S3-DevKitC-1 */
static const int LED_PIN = 48;
static const int NUM_LEDS = 1;

/* Blink periods (ms) */
static const uint32_t SLOW_BLINK_PERIOD = 1000;  /* 1 Hz */
static const uint32_t FAST_BLINK_PERIOD = 333;   /* 3 Hz */

/* LED brightness (0-255) */
static const uint8_t BRIGHTNESS = 20;

/* Colors (GRB order for WS2812) */
static const uint32_t COLOR_OFF    = 0x000000;
static const uint32_t COLOR_GREEN  = 0x00FF00;
static const uint32_t COLOR_YELLOW = 0xFFFF00;
static const uint32_t COLOR_RED    = 0xFF0000;

/* LED states */
typedef enum
{
  LED_STATE_NO_WIFI,        /* Red fast blink (3 Hz) */
  LED_STATE_WAITING,        /* Yellow slow blink (1 Hz) */
  LED_STATE_ACTIVE,         /* Green solid */
  LED_STATE_TIMEOUT         /* Red slow blink (1 Hz) */
} led_state_t;

/* Internal state */
static Adafruit_NeoPixel led (NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
static led_state_t current_state = LED_STATE_WAITING;
static uint32_t watchdog_timeout = 0;
static uint32_t last_poll_time = 0;
static uint32_t last_blink_time = 0;
static int blink_on = 0;
static int ever_polled = 0;

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
 * watchdog_timeout_ms: time after which LED turns red if no POLL received.
 *                      Set to 0 to disable watchdog.
 */
void
led_init (uint32_t watchdog_timeout_ms)
{
  watchdog_timeout = watchdog_timeout_ms;
  current_state = LED_STATE_WAITING;
  last_poll_time = 0;
  last_blink_time = 0;
  blink_on = 0;
  ever_polled = 0;

  led.begin ();
  led.setBrightness (BRIGHTNESS);
  led_set_color (COLOR_OFF);
}

/* For watchdog: track when last poll was notified */
static uint32_t poll_notify_time = 0;
static int poll_time_valid = 0;

/*
 * Notify that a valid POLL was received.
 * Transitions LED to green (communication active).
 */
void
led_notify_poll (void)
{
  ever_polled = 1;
  current_state = LED_STATE_ACTIVE;
  poll_time_valid = 1;  /* Mark that next update should record time */
}

/*
 * Notify that WiFi has connected.
 * Transitions from red (no WiFi) to yellow (waiting for POLL).
 */
void
led_notify_wifi_connected (void)
{
  if (current_state == LED_STATE_NO_WIFI)
    current_state = LED_STATE_WAITING;
}

/*
 * Notify that WiFi has disconnected.
 * Transitions to red fast blink (no WiFi).
 */
void
led_notify_wifi_disconnected (void)
{
  current_state = LED_STATE_NO_WIFI;
}

/*
 * Update LED state machine and output.
 * now_ms: current time in milliseconds (e.g., millis()).
 * Call every loop iteration. Non-blocking.
 */
void
led_update (uint32_t now_ms)
{
  /* Record poll time on first update after notify */
  if (poll_time_valid)
    {
      last_poll_time = now_ms;
      poll_time_valid = 0;
    }

  /* Check watchdog timeout (only after first poll) */
  if (current_state == LED_STATE_ACTIVE && ever_polled && watchdog_timeout > 0)
    {
      if ((now_ms - last_poll_time) >= watchdog_timeout)
        current_state = LED_STATE_TIMEOUT;
    }

  /* Update LED output based on state */
  switch (current_state)
    {
    case LED_STATE_NO_WIFI:
      /* Fast red blink (3 Hz) */
      if ((now_ms - last_blink_time) >= FAST_BLINK_PERIOD)
        {
          blink_on = !blink_on;
          last_blink_time = now_ms;
          led_set_color (blink_on ? COLOR_RED : COLOR_OFF);
        }
      break;

    case LED_STATE_WAITING:
      /* Slow yellow blink (1 Hz) */
      if ((now_ms - last_blink_time) >= SLOW_BLINK_PERIOD)
        {
          blink_on = !blink_on;
          last_blink_time = now_ms;
          led_set_color (blink_on ? COLOR_YELLOW : COLOR_OFF);
        }
      break;

    case LED_STATE_ACTIVE:
      /* Solid green */
      led_set_color (COLOR_GREEN);
      break;

    case LED_STATE_TIMEOUT:
      /* Slow red blink (1 Hz) */
      if ((now_ms - last_blink_time) >= SLOW_BLINK_PERIOD)
        {
          blink_on = !blink_on;
          last_blink_time = now_ms;
          led_set_color (blink_on ? COLOR_RED : COLOR_OFF);
        }
      break;
    }
}
