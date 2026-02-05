/*
 * test_led.c -- Unity tests for tmon LED state machine.
 *
 * Tests state transitions without hardware.
 * Run with: pio test -e native
 */

#include <unity.h>

#include "led.h"

/* State constants (must match led_stub.cpp) */
#define LED_OFF    0
#define LED_ERROR  1
#define LED_TX     2

/* External test helpers from led_stub.cpp */
extern int led_stub_get_state (void);
extern void led_stub_set_state (int state);
extern int led_stub_get_state_before_tx (void);
extern void led_stub_reset (void);

/* -- Initialization tests -------------------------------------------------- */

void
test_init_starts_off (void)
{
  /* LED should start off after init. */
  led_init (90000);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

void
test_init_no_watchdog (void)
{
  /* Init with 0 timeout should also start off. */
  led_init (0);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

/* -- Error state tests ----------------------------------------------------- */

void
test_set_error (void)
{
  /* Setting error should transition to ERROR state. */
  led_init (90000);
  led_error ();
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

void
test_error_persists (void)
{
  /* Error state should persist across updates. */
  led_init (90000);
  led_error ();
  led_update (1000);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
  led_update (2000);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

/* -- TX blink tests -------------------------------------------------------- */

void
test_blink_tx_sets_tx_state (void)
{
  /* led_blink should set TX state. */
  led_init (90000);
  led_blink ();
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());
}

void
test_blink_tx_returns_to_off (void)
{
  /* TX blink should return to OFF after duration. */
  led_init (90000);
  led_blink ();
  led_update (0);  /* Start blink timer */
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());

  led_update (50);  /* Mid-blink */
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());

  led_update (100);  /* Blink complete */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

void
test_blink_tx_returns_to_error (void)
{
  /* TX blink should return to ERROR if that was previous state. */
  led_init (90000);
  led_error ();
  led_blink ();
  led_update (0);
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state_before_tx ());

  led_update (100);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

void
test_multiple_tx_blinks (void)
{
  /* Multiple TX blinks should each complete properly. */
  led_init (90000);

  led_blink ();
  led_update (0);
  led_update (100);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_blink ();
  led_update (200);
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());
  led_update (300);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

/* -- Watchdog tests -------------------------------------------------------- */

void
test_watchdog_triggers_error (void)
{
  /* Watchdog should trigger error after timeout. */
  led_init (1000);  /* 1s watchdog */
  led_blink ();
  led_update (0);  /* Start at time 0, records last_tx_time */
  led_update (100);  /* Blink complete, back to OFF */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_update (500);  /* Still within timeout */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_update (1001);  /* Past timeout (last_tx_time=0, now=1001, diff=1001 >= 1000) */
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

void
test_watchdog_reset_by_tx (void)
{
  /* TX should reset watchdog timer. */
  led_init (1000);
  led_blink ();
  led_update (0);
  led_update (100);  /* Blink complete */

  led_update (800);  /* Near timeout */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_blink ();   /* Reset watchdog */
  led_update (800);  /* New start time */
  led_update (900);

  led_update (1700);  /* Would have timed out without reset */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_update (1800);  /* Now times out (800 + 1000) */
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

void
test_no_watchdog_when_disabled (void)
{
  /* No watchdog when timeout is 0. */
  led_init (0);  /* Disabled */
  led_blink ();
  led_update (0);
  led_update (100);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  led_update (1000000);  /* Way past any timeout */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

void
test_no_watchdog_before_first_tx (void)
{
  /* Watchdog should not trigger before first TX. */
  led_init (1000);
  led_update (0);
  led_update (2000);  /* Way past timeout */
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

void
test_tx_recovers_from_watchdog_error (void)
{
  /* TX after watchdog error should show green briefly. */
  led_init (1000);
  led_blink ();
  led_update (0);
  led_update (100);  /* Back to OFF */
  led_update (1001);  /* Timeout -> ERROR */
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());

  /* TX should still blink green */
  led_blink ();
  TEST_ASSERT_EQUAL (LED_TX, led_stub_get_state ());
  led_update (1001);
  led_update (1101);
  /* Returns to ERROR since that was state_before_tx */
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

/* -- Update tests ---------------------------------------------------------- */

void
test_update_is_nonblocking (void)
{
  /* led_update should return without blocking. */
  led_init (90000);
  led_update (0);
  led_update (1000);
  led_update (2000);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

/* -- Unity setup/teardown -------------------------------------------------- */

void
setUp (void)
{
  led_stub_reset ();
}

void
tearDown (void)
{
}

int
main (void)
{
  UNITY_BEGIN ();

  RUN_TEST (test_init_starts_off);
  RUN_TEST (test_init_no_watchdog);

  RUN_TEST (test_set_error);
  RUN_TEST (test_error_persists);

  RUN_TEST (test_blink_tx_sets_tx_state);
  RUN_TEST (test_blink_tx_returns_to_off);
  RUN_TEST (test_blink_tx_returns_to_error);
  RUN_TEST (test_multiple_tx_blinks);

  RUN_TEST (test_watchdog_triggers_error);
  RUN_TEST (test_watchdog_reset_by_tx);
  RUN_TEST (test_no_watchdog_when_disabled);
  RUN_TEST (test_no_watchdog_before_first_tx);
  RUN_TEST (test_tx_recovers_from_watchdog_error);

  RUN_TEST (test_update_is_nonblocking);

  return UNITY_END ();
}
