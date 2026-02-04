/*
 * test_led.c -- Unity tests for tmon LED state machine.
 *
 * Tests state transitions without hardware.
 * Run with: pio test -e native
 */

#include <unity.h>

#include "led.h"

/* State constants (must match led_stub.c) */
#define LED_STATE_NO_WIFI  0
#define LED_STATE_WAITING  1
#define LED_STATE_ACTIVE   2
#define LED_STATE_TIMEOUT  3

/* External test helpers from led_stub.c */
extern int led_stub_get_state (void);
extern void led_stub_set_state (int state);
extern void led_stub_trigger_timeout (void);
extern void led_stub_reset (void);

/* -- State transition tests ------------------------------------------------ */

void
test_init_starts_in_waiting (void)
{
  /* UART build starts in WAITING state (yellow blink). */
  led_init (90000);
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());
}

void
test_poll_transitions_to_active (void)
{
  /* Receiving a POLL should transition to ACTIVE (green). */
  led_init (90000);
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());

  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());
}

void
test_active_stays_active_on_poll (void)
{
  /* Multiple POLLs keep us in ACTIVE state. */
  led_init (90000);
  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());
}

void
test_timeout_after_poll (void)
{
  /* After being active, timeout should transition to TIMEOUT (red blink). */
  led_init (90000);
  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  /* Simulate watchdog timeout */
  led_stub_trigger_timeout ();
  TEST_ASSERT_EQUAL (LED_STATE_TIMEOUT, led_stub_get_state ());
}

void
test_no_timeout_before_first_poll (void)
{
  /* Timeout should not occur if we never received a poll (stay in waiting). */
  led_init (90000);
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());

  /* Timeout trigger should have no effect before first poll */
  led_stub_trigger_timeout ();
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());
}

void
test_poll_recovers_from_timeout (void)
{
  /* A new POLL after timeout should return to ACTIVE. */
  led_init (90000);
  led_notify_poll ();
  led_stub_trigger_timeout ();
  TEST_ASSERT_EQUAL (LED_STATE_TIMEOUT, led_stub_get_state ());

  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());
}

/* -- WiFi state tests ------------------------------------------------------ */

void
test_wifi_disconnected_goes_to_no_wifi (void)
{
  /* WiFi disconnect should go to NO_WIFI state (fast red blink). */
  led_init (90000);
  led_notify_wifi_disconnected ();
  TEST_ASSERT_EQUAL (LED_STATE_NO_WIFI, led_stub_get_state ());
}

void
test_wifi_connected_goes_to_waiting (void)
{
  /* WiFi connect from NO_WIFI should go to WAITING. */
  led_init (90000);
  led_notify_wifi_disconnected ();
  TEST_ASSERT_EQUAL (LED_STATE_NO_WIFI, led_stub_get_state ());

  led_notify_wifi_connected ();
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());
}

void
test_wifi_connected_no_effect_when_active (void)
{
  /* WiFi connected notification should not change ACTIVE state. */
  led_init (90000);
  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  led_notify_wifi_connected ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());
}

void
test_wifi_disconnect_from_active (void)
{
  /* WiFi disconnect should go to NO_WIFI even from ACTIVE. */
  led_init (90000);
  led_notify_poll ();
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  led_notify_wifi_disconnected ();
  TEST_ASSERT_EQUAL (LED_STATE_NO_WIFI, led_stub_get_state ());
}

void
test_wifi_full_cycle (void)
{
  /* Full WiFi cycle: NO_WIFI -> WAITING -> ACTIVE -> TIMEOUT -> ACTIVE. */
  led_init (90000);
  led_notify_wifi_disconnected ();  /* Start with no WiFi */
  TEST_ASSERT_EQUAL (LED_STATE_NO_WIFI, led_stub_get_state ());

  led_notify_wifi_connected ();     /* WiFi connects */
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());

  led_notify_poll ();               /* First POLL */
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());

  led_stub_trigger_timeout ();      /* Timeout */
  TEST_ASSERT_EQUAL (LED_STATE_TIMEOUT, led_stub_get_state ());

  led_notify_poll ();               /* Recovery */
  TEST_ASSERT_EQUAL (LED_STATE_ACTIVE, led_stub_get_state ());
}

void
test_wifi_reconnect_after_disconnect (void)
{
  /* WiFi reconnect after active->disconnect should go to WAITING. */
  led_init (90000);
  led_notify_poll ();
  led_notify_wifi_disconnected ();
  TEST_ASSERT_EQUAL (LED_STATE_NO_WIFI, led_stub_get_state ());

  led_notify_wifi_connected ();
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());
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
  TEST_ASSERT_EQUAL (LED_STATE_WAITING, led_stub_get_state ());
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

  RUN_TEST (test_init_starts_in_waiting);
  RUN_TEST (test_poll_transitions_to_active);
  RUN_TEST (test_active_stays_active_on_poll);
  RUN_TEST (test_timeout_after_poll);
  RUN_TEST (test_no_timeout_before_first_poll);
  RUN_TEST (test_poll_recovers_from_timeout);

  RUN_TEST (test_wifi_disconnected_goes_to_no_wifi);
  RUN_TEST (test_wifi_connected_goes_to_waiting);
  RUN_TEST (test_wifi_connected_no_effect_when_active);
  RUN_TEST (test_wifi_disconnect_from_active);
  RUN_TEST (test_wifi_full_cycle);
  RUN_TEST (test_wifi_reconnect_after_disconnect);

  RUN_TEST (test_update_is_nonblocking);

  return UNITY_END ();
}
