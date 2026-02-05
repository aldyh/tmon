/*
 * led.h -- Status LED driver for tmon slave
 */

#ifndef TMON_LED_H
#define TMON_LED_H

#include <stdint.h>

void led_init (uint32_t timeout_ms);
void led_error (void);
void led_blink (void);
void led_update (uint32_t now_ms);

#endif /* TMON_LED_H */
