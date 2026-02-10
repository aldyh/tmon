/*
 * led_stub.cpp -- Stub LED driver for native tests
 *
 * Tracks LED state machine without actual hardware.
 * Three states: OFF (0), ERROR (1), IDENTIFY (2).
 */

#include "led.h"

/* LED states (matches led.cpp) */
typedef enum
{
  LED_OFF,
  LED_ERROR,
  LED_IDENTIFY
} led_state_t;

/* Internal state */
static led_state_t current_state = LED_OFF;
static uint32_t last_toggle_ms = 0;
static int led_on = 0;

/* Identify sequence state */
static led_state_t saved_state = LED_OFF;
static uint8_t identify_total = 0;
static uint8_t identify_count = 0;

/*
 * Restore the saved state after identify sequence completes.
 */
static void
led_restore (void)
{
  current_state = saved_state;
  identify_total = 0;
  identify_count = 0;

  if (current_state == LED_ERROR)
    {
      last_toggle_ms = 0;
      led_on = 1;
    }
  else
    {
      led_on = 0;
    }
}

void
led_init (void)
{
  current_state = LED_OFF;
  last_toggle_ms = 0;
  led_on = 0;
  saved_state = LED_OFF;
  identify_total = 0;
  identify_count = 0;
}

void
led_error (void)
{
  if (current_state == LED_IDENTIFY)
    {
      saved_state = LED_ERROR;
      return;
    }
  current_state = LED_ERROR;
  last_toggle_ms = 0;
  led_on = 1;
}

void
led_clear (void)
{
  if (current_state == LED_IDENTIFY)
    {
      saved_state = LED_OFF;
      return;
    }
  current_state = LED_OFF;
  led_on = 0;
}

void
led_identify (uint8_t count)
{
  if (count == 0)
    return;

  if (current_state != LED_IDENTIFY)
    saved_state = current_state;

  current_state = LED_IDENTIFY;
  identify_total = count;
  identify_count = 0;
  last_toggle_ms = 0;
  led_on = 1;
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

  if (current_state == LED_ERROR)
    {
      if ((now_ms - last_toggle_ms) >= 500)
        {
          led_on = !led_on;
          last_toggle_ms = now_ms;
        }
      return;
    }

  /* LED_IDENTIFY (300ms interval) */
  if ((now_ms - last_toggle_ms) >= 300)
    {
      if (led_on)
        {
          led_on = 0;
          identify_count++;
          last_toggle_ms = now_ms;

          if (identify_count >= identify_total)
            led_restore ();
        }
      else
        {
          led_on = 1;
          last_toggle_ms = now_ms;
        }
    }
}

/* -- Test helpers (not in header) ----------------------------------------- */

/*
 * Get current LED state as integer.
 *   0 = OFF, 1 = ERROR, 2 = IDENTIFY
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
 * Get whether the identify sequence has finished.
 */
int
led_stub_get_identify_done (void)
{
  return (current_state != LED_IDENTIFY);
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
  saved_state = LED_OFF;
  identify_total = 0;
  identify_count = 0;
}
