/*
 * led.h -- Status LED driver for tmon client
 *
 * All blink functions are blocking.  The LED is off between calls.
 */

#ifndef TMON_LED_H
#define TMON_LED_H

#include <stdint.h>

void led_init (void);
void led_identify (uint8_t count);
void led_error_blink (uint8_t count);
void led_tx_blink (void);

#endif /* TMON_LED_H */
