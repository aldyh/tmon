/*
 * led.h -- Status LED driver for tmon slave
 *
 * Two states: OFF (normal) and ERROR (blinking red).
 */

#ifndef TMON_LED_H
#define TMON_LED_H

#include <stdint.h>

void led_init (void);
void led_error (void);
void led_clear (void);
void led_update (uint32_t now_ms);

#endif /* TMON_LED_H */
