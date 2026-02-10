/*
 * led.h -- Status LED driver for tmon slave
 *
 * Two states: OFF (normal) and ERROR (blinking red).
 * led_identify() is a blocking call that blinks yellow N times,
 * then restores the prior state.
 */

#ifndef TMON_LED_H
#define TMON_LED_H

#include <stdint.h>

void led_init (void);
void led_error (void);
void led_clear (void);
void led_identify (uint8_t count);
void led_update (uint32_t now_ms);

#endif /* TMON_LED_H */
