/*
 * test_led.cpp -- Unity tests for tmon LED state machine.
 *
 * Tests state transitions without hardware.
 * Run with: pio test -e native
 */

#include <unity.h>

#include "led.h"

/* State constants (must match led_stub.cpp) */
#define LED_OFF    0
#define LED_ERROR  1

/* External test helpers from led_stub.cpp */
extern int led_stub_get_state (void);
extern int led_stub_get_led_on (void);
extern void led_stub_reset (void);

/* -- Initialization -------------------------------------------------------- */

void
test_init_starts_off (void)
{
  /* LED should start off after init. */
  led_init ();
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
}

/* -- Error state ----------------------------------------------------------- */

void
test_set_error (void)
{
  /* Setting error should transition to ERROR state with LED on. */
  led_init ();
  led_error ();
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());
}

void
test_error_persists (void)
{
  /* Error state should persist across updates. */
  led_init ();
  led_error ();
  led_update (1000);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
  led_update (2000);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
}

/* -- Blinking -------------------------------------------------------------- */

void
test_error_blinks (void)
{
  /* Error state toggles LED every 500ms. */
  led_init ();
  led_error ();
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* First update records the start time */
  led_update (1000);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Before interval: still on */
  led_update (1400);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* At interval: toggles off */
  led_update (1500);
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());

  /* Another interval: toggles back on */
  led_update (2000);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());
}

/* -- Clear ----------------------------------------------------------------- */

void
test_clear_turns_off (void)
{
  /* Clear after error returns to OFF. */
  led_init ();
  led_error ();
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());

  led_clear ();
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
}

void
test_clear_stops_blinking (void)
{
  /* Clear during blink stops it. */
  led_init ();
  led_error ();
  led_update (1000);
  led_update (1500);  /* toggled off */
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());

  led_clear ();
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());

  /* Further updates do nothing. */
  led_update (2000);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
}

/* -- Update when OFF ------------------------------------------------------- */

void
test_update_when_off_does_nothing (void)
{
  /* Update in OFF state is a no-op. */
  led_init ();
  led_update (0);
  led_update (1000);
  led_update (999999);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
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

  RUN_TEST (test_set_error);
  RUN_TEST (test_error_persists);
  RUN_TEST (test_error_blinks);

  RUN_TEST (test_clear_turns_off);
  RUN_TEST (test_clear_stops_blinking);

  RUN_TEST (test_update_when_off_does_nothing);

  return UNITY_END ();
}
