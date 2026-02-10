/*
 * led_stub.cpp -- Stub LED driver for native tests
 *
 * Tracks LED state machine without actual hardware.
 * Two states: OFF (0), ERROR (1).
 *
 * led_identify() records that it was called (for test assertions)
 * and restores the previous state, matching the real blocking behavior.
 */

#include "led.h"

/* LED states (matches led.cpp) */
typedef enum
{
  LED_OFF,
  LED_ERROR
} led_state_t;

/* Internal state */
static led_state_t current_state = LED_OFF;
static uint32_t last_toggle_ms = 0;
static int led_on = 0;

/* Identify tracking for test assertions */
static int identify_call_count = 0;
static uint8_t identify_last_n = 0;

void
led_init (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;
  identify_call_count = 0;
  identify_last_n = 0;
}

void
led_error (void)
{
  current_state = LED_ERROR;
  last_toggle_ms = 0;
  led_on = 1;
}

void
led_clear (void)
{
  current_state = LED_OFF;
  led_on = 0;
}

/*
 * Stub identify: record the call, then restore previous state.
 *
 * In the real driver this blocks for count * 600ms.  The stub
 * simulates the net effect: state before == state after.
 */
void
led_identify (uint8_t count)
{
  if (count == 0)
    return;

  identify_call_count++;
  identify_last_n = count;

  /* State is unchanged -- matches blocking behavior on real hardware */
}

void
led_update (uint32_t now_ms)
{
  if (current_state == LED_OFF)
    return;

  if (last_toggle_ms == 0)
    {
      last_toggle_ms = now_ms;
      return;
    }

  if ((now_ms - last_toggle_ms) >= 500)
    {
      led_on = !led_on;
      last_toggle_ms = now_ms;
    }
}

/* -- Test helpers (not in header) ----------------------------------------- */

/*
 * Get current LED state as integer.
 *   0 = OFF, 1 = ERROR
 */
int
led_stub_get_state (void)
{
  return (int) current_state;
}

/*
 * Get whether the LED is currently lit.
 */
int
led_stub_get_led_on (void)
{
  return led_on;
}

/*
 * Get the number of times led_identify() was called (with count > 0).
 */
int
led_stub_get_identify_call_count (void)
{
  return identify_call_count;
}

/*
 * Get the count argument from the last led_identify() call.
 */
uint8_t
led_stub_get_identify_last_n (void)
{
  return identify_last_n;
}

/*
 * Reset stub state for testing.
 */
void
led_stub_reset (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;
  identify_call_count = 0;
  identify_last_n = 0;
}
