/*
 * config.cpp -- Binary-patchable configuration for tmon slave
 *
 * Marker arrays contain @@MARKER_XXX@@ strings in unpatched firmware.
 * deploy/tmon-patch overwrites the marker region with real values
 * (binary for numerics, null-terminated for strings).
 *
 * config_init() reads the patched bytes into cfg_* variables.
 */

#include "config.h"

/*
 * Marker arrays -- patcher finds these by byte pattern and overwrites.
 * Each @@MARKER_XXXX@@ is 15 chars + null = 16 bytes.
 *
 * Numeric fields: patcher writes raw binary, firmware reads directly.
 */
uint8_t cfg_addr[16] = "@@MARKER_ADDR@@";

/* Parsed configuration */
uint8_t cfg_slave_addr = 0;

/*
 * config_init -- Parse patched marker arrays into config variables.
 *
 * For addr: byte 0 holds the slave address (1-247).
 * Unpatched marker has '@' (0x40) in byte 0, which is outside valid range.
 */
void
config_init (void)
{
  cfg_slave_addr = cfg_addr[0];
}
