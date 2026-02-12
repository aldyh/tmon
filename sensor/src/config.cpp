/*
 * config.cpp -- Binary-patchable configuration for tmon slave
 *
 * Marker arrays contain @@MARKER_XXX@@ strings in unpatched firmware.
 * deploy/tmon-patch overwrites the marker region with real values
 * (binary for numerics, null-terminated for strings).
 *
 * config_init() reads the patched bytes into config_* variables.
 */

#include "config.h"
#include <string.h>

/*
 * Marker arrays -- patcher finds these by byte pattern and overwrites.
 * Each @@MARKER_XXXX@@ is 15 chars + null = 16 bytes.
 *
 * Numeric fields: patcher writes raw little-endian binary.
 * String fields: patcher writes null-terminated string + null padding.
 */
uint8_t config_addr[16] = "@@MARKER_ADDR@@";
uint8_t config_port[16] = "@@MARKER_PORT@@";
uint8_t config_push[16] = "@@MARKER_PUSH@@";
char    config_ssid_buf[33] = "@@MARKER_SSID@@";
char    config_pass_buf[65] = "@@MARKER_PASS@@";
char    config_host_buf[65] = "@@MARKER_HOST@@";

/* Parsed configuration */
uint8_t  config_slave_addr   = 0;
char     config_ssid[33]     = "";
char     config_pass[65]     = "";
char     config_host[65]     = "";
uint16_t config_master_port  = 0;
uint16_t config_push_interval = 0;

/*
 * config_init -- Parse patched marker arrays into config variables.
 *
 * For addr: byte 0 holds the slave address (1-247).
 * For port/push: bytes 0-1 hold a little-endian uint16.
 * For strings: null-terminated value copied from marker buffer.
 */
void
config_init (void)
{
  config_slave_addr = config_addr[0];
  config_master_port = (uint16_t)(config_port[0] | (config_port[1] << 8));
  config_push_interval = (uint16_t)(config_push[0] | (config_push[1] << 8));
  memcpy (config_ssid, config_ssid_buf, sizeof (config_ssid));
  memcpy (config_pass, config_pass_buf, sizeof (config_pass));
  memcpy (config_host, config_host_buf, sizeof (config_host));
}
