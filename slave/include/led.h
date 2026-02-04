/*
 * led.h -- Status LED driver for tmon slave
 *
 * Uses the built-in WS2812 RGB LED (GPIO 48 on ESP32-S3) to signal
 * connection/communication state.
 *
 * LED states:
 *   Green solid       - Recent POLL received (communication active)
 *   Yellow solid      - Waiting for first POLL
 *   Red fast blink    - No WiFi connection (3 Hz, WiFi build only)
 *   Red slow blink    - Watchdog timeout, no POLL for too long (1 Hz)
 */

#ifndef TMON_LED_H
#define TMON_LED_H

#include <stdint.h>

void led_init (uint32_t watchdog_timeout_ms);
void led_notify_ready (void);
void led_notify_poll (void);
void led_notify_wifi_disconnected (void);
void led_update (uint32_t now_ms);

#endif /* TMON_LED_H */
