/*
 * led_stub.cpp -- Stub LED driver for native tests
 *
 * Tracks LED state machine without actual hardware.
 * Two states: OFF (0) and ERROR (1).
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

void
led_init (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;
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
 * Reset stub state for testing.
 */
void
led_stub_reset (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;
}
