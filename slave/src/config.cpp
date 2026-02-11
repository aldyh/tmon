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
#include <string.h>

/*
 * Marker arrays -- patcher finds these by byte pattern and overwrites.
 * Each @@MARKER_XXXX@@ is 15 chars + null = 16 bytes.
 *
 * Numeric fields: patcher writes raw little-endian binary.
 * String fields: patcher writes null-terminated string + null padding.
 */
uint8_t cfg_addr[16] = "@@MARKER_ADDR@@";
uint8_t cfg_port[16] = "@@MARKER_PORT@@";
uint8_t cfg_push[16] = "@@MARKER_PUSH@@";
char    cfg_ssid_buf[33] = "@@MARKER_SSID@@";
char    cfg_pass_buf[65] = "@@MARKER_PASS@@";
char    cfg_host_buf[65] = "@@MARKER_HOST@@";

/* Parsed configuration */
uint8_t  cfg_slave_addr   = 0;
char     cfg_ssid[33]     = "";
char     cfg_pass[65]     = "";
char     cfg_host[65]     = "";
uint16_t cfg_master_port  = 0;
uint16_t cfg_push_interval = 0;

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
  cfg_slave_addr = cfg_addr[0];
  cfg_master_port = (uint16_t)(cfg_port[0] | (cfg_port[1] << 8));
  cfg_push_interval = (uint16_t)(cfg_push[0] | (cfg_push[1] << 8));
  memcpy (cfg_ssid, cfg_ssid_buf, sizeof (cfg_ssid));
  memcpy (cfg_pass, cfg_pass_buf, sizeof (cfg_pass));
  memcpy (cfg_host, cfg_host_buf, sizeof (cfg_host));
}
