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
  LED_OFF,    /* LED off (normal) */
  LED_ERROR,  /* Solid red */
  LED_TX      /* Blinking green (auto-returns to previous) */
} led_state_t;

/* Internal state */
static led_state_t current_state = LED_OFF;
static led_state_t state_before_tx = LED_OFF;
static uint32_t watchdog_timeout = 0;
static uint32_t last_tx_time = 0;
static uint32_t tx_blink_start = 0;
static int tx_pending = 0;
static int ever_transmitted = 0;

void
led_init (uint32_t timeout_ms)
{
  watchdog_timeout = timeout_ms;
  current_state = LED_OFF;
  state_before_tx = LED_OFF;
  last_tx_time = 0;
  tx_blink_start = 0;
  tx_pending = 0;
  ever_transmitted = 0;
}

void
led_error (void)
{
  current_state = LED_ERROR;
  state_before_tx = LED_ERROR;
}

void
led_blink (void)
{
  state_before_tx = LED_OFF;
  current_state = LED_TX;
  tx_pending = 1;
}

void
led_update (uint32_t now_ms)
{
  /* Record TX time if blink just started */
  if (current_state == LED_TX && tx_pending)
    {
      tx_blink_start = now_ms;
      last_tx_time = now_ms;
      ever_transmitted = 1;
      tx_pending = 0;
    }

  /* Handle TX blink timeout (100ms) */
  if (current_state == LED_TX)
    {
      if ((now_ms - tx_blink_start) >= 100)
        current_state = state_before_tx;
      return;
    }

  /* Check watchdog timeout */
  if (watchdog_timeout > 0 && ever_transmitted)
    {
      if ((now_ms - last_tx_time) >= watchdog_timeout)
        {
          current_state = LED_ERROR;
          state_before_tx = LED_ERROR;
        }
    }
}

/* -- Test helpers (not in header) ----------------------------------------- */

/*
 * Get current LED state as integer.
 *   0 = OFF, 1 = ERROR, 2 = TX
 */
int
led_stub_get_state (void)
{
  return (int) current_state;
}

/*
 * Set current state directly (for testing).
 */
void
led_stub_set_state (int state)
{
  current_state = (led_state_t) state;
}

/*
 * Get the state the LED will return to after TX blink.
 */
int
led_stub_get_state_before_tx (void)
{
  return (int) state_before_tx;
}

/*
 * Reset stub state for testing.
 */
void
led_stub_reset (void)
{
  current_state = LED_OFF;
  state_before_tx = LED_OFF;
  watchdog_timeout = 0;
  last_tx_time = 0;
  tx_blink_start = 0;
  tx_pending = 0;
  ever_transmitted = 0;
}
