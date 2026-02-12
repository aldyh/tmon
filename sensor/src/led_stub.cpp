/*
 * led_stub.cpp -- Stub LED driver for native tests
 *
 * Records calls for test assertions.  No hardware interaction.
 */

#include "led.h"

/* Call tracking */
static int identify_call_count = 0;
static uint8_t identify_last_n = 0;
static int error_blink_call_count = 0;
static uint8_t error_blink_last_n = 0;
static int tx_blink_call_count = 0;

void
led_init (void)
{
  identify_call_count = 0;
  identify_last_n = 0;
  error_blink_call_count = 0;
  error_blink_last_n = 0;
  tx_blink_call_count = 0;
}

void
led_identify (uint8_t count)
{
  identify_call_count++;
  identify_last_n = count;
}

void
led_error_blink (uint8_t count)
{
  error_blink_call_count++;
  error_blink_last_n = count;
}

void
led_tx_blink (void)
{
  tx_blink_call_count++;
}

/* -- Test helpers (not in header) ----------------------------------------- */

int
led_stub_get_identify_call_count (void)
{
  return identify_call_count;
}

uint8_t
led_stub_get_identify_last_n (void)
{
  return identify_last_n;
}

int
led_stub_get_error_blink_call_count (void)
{
  return error_blink_call_count;
}

uint8_t
led_stub_get_error_blink_last_n (void)
{
  return error_blink_last_n;
}

int
led_stub_get_tx_blink_call_count (void)
{
  return tx_blink_call_count;
}

void
led_stub_reset (void)
{
  identify_call_count = 0;
  identify_last_n = 0;
  error_blink_call_count = 0;
  error_blink_last_n = 0;
  tx_blink_call_count = 0;
}
