/*
 * config.h -- Binary-patchable configuration for tmon client
 *
 * Marker arrays are initialized with @@MARKER_XXX@@ strings at compile
 * time.  The deploy/tmon-patch script overwrites these markers with real
 * values in the firmware binary before flashing.
 *
 * config_init() reads the (possibly patched) marker arrays into the
 * config_* variables that firmware code uses at runtime.
 */

#ifndef TMON_CONFIG_H
#define TMON_CONFIG_H

#include <stdint.h>

/* Parsed configuration -- set by config_init() */
extern uint8_t  config_client_addr;
extern char     config_ssid[33];
extern char     config_pass[65];
extern char     config_host[65];
extern uint16_t config_server_port;
extern uint16_t config_push_interval;

void config_init (void);

#endif /* TMON_CONFIG_H */
