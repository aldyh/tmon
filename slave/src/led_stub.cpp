/*
 * led_stub.c -- Stub LED driver for native tests
 *
 * Tracks LED state machine without actual hardware.
 * Provides test helpers to query internal state.
 */

#include "led.h"

/* LED states (matches led.cpp) */
typedef enum
{
  LED_STATE_NO_WIFI,        /* Red fast blink (3 Hz) */
  LED_STATE_WAITING,        /* Yellow slow blink (1 Hz) */
  LED_STATE_ACTIVE,         /* Green solid */
  LED_STATE_TIMEOUT         /* Red slow blink (1 Hz) */
} led_state_t;

/* Internal state */
static led_state_t current_state = LED_STATE_WAITING;
static uint32_t watchdog_timeout = 0;
static uint32_t last_poll_time = 0;
static int ever_polled = 0;

void
led_init (uint32_t watchdog_timeout_ms)
{
  watchdog_timeout = watchdog_timeout_ms;
  current_state = LED_STATE_WAITING;
  last_poll_time = 0;
  ever_polled = 0;
}

void
led_notify_poll (void)
{
  ever_polled = 1;
  current_state = LED_STATE_ACTIVE;
}

void
led_notify_ready (void)
{
  if (current_state == LED_STATE_NO_WIFI)
    current_state = LED_STATE_WAITING;
}

void
led_notify_wifi_disconnected (void)
{
  current_state = LED_STATE_NO_WIFI;
}

void
led_update (uint32_t now_ms)
{
  last_poll_time = now_ms;

  /* Check watchdog timeout (only after we've received at least one poll) */
  if (current_state == LED_STATE_ACTIVE && watchdog_timeout > 0 && ever_polled)
    {
      /* Note: actual impl tracks last_poll_time differently; here we use
         a simplified model where the test manually advances time */
    }
}

/* -- Test helpers (not in header) ----------------------------------------- */

/*
 * Get current LED state as integer.
 *   0 = NO_WIFI, 1 = WAITING, 2 = ACTIVE, 3 = TIMEOUT
 */
int
led_stub_get_state (void)
{
  return (int) current_state;
}

/*
 * Set current state directly (for watchdog timeout testing).
 */
void
led_stub_set_state (int state)
{
  current_state = (led_state_t) state;
}

/*
 * Simulate watchdog timeout transition.
 * Call this to test timeout behavior.
 */
void
led_stub_trigger_timeout (void)
{
  if (ever_polled && current_state == LED_STATE_ACTIVE)
    current_state = LED_STATE_TIMEOUT;
}

/*
 * Reset stub state for testing.
 */
void
led_stub_reset (void)
{
  current_state = LED_STATE_WAITING;
  watchdog_timeout = 0;
  last_poll_time = 0;
  ever_polled = 0;
}
