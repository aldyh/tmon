/*
 * config.h -- Binary-patchable configuration for tmon slave
 *
 * Marker arrays are initialized with @@MARKER_XXX@@ strings at compile
 * time.  The deploy/tmon-patch script overwrites these markers with real
 * values in the firmware binary before flashing.
 *
 * config_init() reads the (possibly patched) marker arrays into the
 * cfg_* variables that firmware code uses at runtime.
 */

#ifndef TMON_CONFIG_H
#define TMON_CONFIG_H

#include <stdint.h>

/* Parsed configuration -- set by config_init() */
extern uint8_t  cfg_slave_addr;

void config_init (void);

#endif /* TMON_CONFIG_H */
