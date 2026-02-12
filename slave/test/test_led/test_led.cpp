/*
 * test_led.cpp -- Unity tests for tmon LED module.
 *
 * Tests the stub records calls correctly.
 * Run with: pio test -e native
 */

#include <unity.h>

#include "led.h"

/* External test helpers from led_stub.cpp */
extern int led_stub_get_identify_call_count (void);
extern uint8_t led_stub_get_identify_last_n (void);
extern int led_stub_get_error_blink_call_count (void);
extern uint8_t led_stub_get_error_blink_last_n (void);
extern int led_stub_get_tx_blink_call_count (void);
extern void led_stub_reset (void);

/* -- Initialization -------------------------------------------------------- */

void
test_init_resets_counters (void)
{
  /* Init clears all call tracking. */
  led_identify (1);
  led_error_blink (1);
  led_init ();
  TEST_ASSERT_EQUAL (0, led_stub_get_identify_call_count ());
  TEST_ASSERT_EQUAL (0, led_stub_get_error_blink_call_count ());
  TEST_ASSERT_EQUAL (0, led_stub_get_tx_blink_call_count ());
}

/* -- Identify -------------------------------------------------------------- */

void
test_identify_records_call (void)
{
  /* Identify records each call and the count argument. */
  led_identify (3);
  TEST_ASSERT_EQUAL (1, led_stub_get_identify_call_count ());
  TEST_ASSERT_EQUAL (3, led_stub_get_identify_last_n ());

  led_identify (5);
  TEST_ASSERT_EQUAL (2, led_stub_get_identify_call_count ());
  TEST_ASSERT_EQUAL (5, led_stub_get_identify_last_n ());
}

/* -- Error blink ----------------------------------------------------------- */

void
test_error_blink_records_call (void)
{
  /* Error blink records each call and the count argument. */
  led_error_blink (2);
  TEST_ASSERT_EQUAL (1, led_stub_get_error_blink_call_count ());
  TEST_ASSERT_EQUAL (2, led_stub_get_error_blink_last_n ());
}

/* -- TX blink -------------------------------------------------------------- */

void
test_tx_blink_records_call (void)
{
  /* TX blink records each call. */
  led_tx_blink ();
  TEST_ASSERT_EQUAL (1, led_stub_get_tx_blink_call_count ());

  led_tx_blink ();
  TEST_ASSERT_EQUAL (2, led_stub_get_tx_blink_call_count ());
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

  RUN_TEST (test_init_resets_counters);

  RUN_TEST (test_identify_records_call);

  RUN_TEST (test_error_blink_records_call);

  RUN_TEST (test_tx_blink_records_call);

  return UNITY_END ();
}
