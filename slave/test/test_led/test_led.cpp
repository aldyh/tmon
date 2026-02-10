/*
 * test_led.cpp -- Unity tests for tmon LED state machine.
 *
 * Tests state transitions without hardware.
 * Run with: pio test -e native
 */

#include <unity.h>

#include "led.h"

/* State constants (must match led_stub.cpp) */
#define LED_OFF       0
#define LED_ERROR     1
#define LED_IDENTIFY  2

/* External test helpers from led_stub.cpp */
extern int led_stub_get_state (void);
extern int led_stub_get_led_on (void);
extern int led_stub_get_identify_done (void);
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

/* -- Identify -------------------------------------------------------------- */

void
test_identify_blinks_n_times (void)
{
  /* Identify with count=3 blinks 3 times then returns to OFF. */
  led_init ();
  led_identify (3);
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* First update records start time */
  led_update (1000);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Blink 1: off at 1300 */
  led_update (1300);
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Blink 1: on at 1600 */
  led_update (1600);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Blink 2: off at 1900 */
  led_update (1900);
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Blink 2: on at 2200 */
  led_update (2200);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Blink 3: off at 2500 -- sequence done, restores to OFF */
  led_update (2500);
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_identify_done ());
}

void
test_identify_restores_error (void)
{
  /* Identify during error restores to ERROR when done. */
  led_init ();
  led_error ();
  led_update (100);  /* record start time for error blink */

  led_identify (1);
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* First update records start time */
  led_update (1000);

  /* Blink 1: off at 1300 -- done, restores to ERROR */
  led_update (1300);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());
}

void
test_identify_zero_is_noop (void)
{
  /* Identify with count=0 does nothing. */
  led_init ();
  led_identify (0);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
}

void
test_identify_restart_mid_sequence (void)
{
  /* Calling identify again mid-sequence restarts from beginning. */
  led_init ();
  led_identify (3);
  led_update (1000);
  led_update (1300);  /* blink 1 off */
  led_update (1600);  /* blink 2 on */

  /* Restart with count=2 */
  led_identify (2);
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Record start time */
  led_update (2000);

  /* Blink 1: off at 2300 */
  led_update (2300);
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Blink 1: on at 2600 */
  led_update (2600);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  /* Blink 2: off at 2900 -- done */
  led_update (2900);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
}

void
test_error_during_identify_updates_saved (void)
{
  /* led_error() during identify updates saved state, not current. */
  led_init ();
  led_identify (1);
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  led_error ();
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Complete identify -- should restore to ERROR */
  led_update (1000);
  led_update (1300);
  TEST_ASSERT_EQUAL (LED_ERROR, led_stub_get_state ());
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());
}

void
test_clear_during_identify_updates_saved (void)
{
  /* led_clear() during identify updates saved state, not current. */
  led_init ();
  led_error ();
  led_update (100);

  led_identify (1);
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Clear during identify -- saved state becomes OFF */
  led_clear ();
  TEST_ASSERT_EQUAL (LED_IDENTIFY, led_stub_get_state ());

  /* Complete identify -- should restore to OFF, not ERROR */
  led_update (1000);
  led_update (1300);
  TEST_ASSERT_EQUAL (LED_OFF, led_stub_get_state ());
  TEST_ASSERT_EQUAL (0, led_stub_get_led_on ());
}

void
test_identify_single_blink (void)
{
  /* Identify with count=1 blinks once then stops. */
  led_init ();
  led_identify (1);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  led_update (1000);
  TEST_ASSERT_EQUAL (1, led_stub_get_led_on ());

  led_update (1300);
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

  RUN_TEST (test_identify_blinks_n_times);
  RUN_TEST (test_identify_restores_error);
  RUN_TEST (test_identify_zero_is_noop);
  RUN_TEST (test_identify_restart_mid_sequence);
  RUN_TEST (test_error_during_identify_updates_saved);
  RUN_TEST (test_clear_during_identify_updates_saved);
  RUN_TEST (test_identify_single_blink);

  return UNITY_END ();
}
