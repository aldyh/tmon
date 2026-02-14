/*
 * handler.h -- Protocol message handler for tmon sensor
 *
 * Processes incoming POLL requests and builds REPLY responses.
 * Transport-agnostic: works with UART or WiFi.
 */

#ifndef TMON_HANDLER_H
#define TMON_HANDLER_H

#include <stddef.h>
#include <stdint.h>

size_t tmon_handler_build_reply (uint8_t *buf, size_t buf_len, uint8_t addr);

size_t tmon_handler_process (uint8_t my_addr, const uint8_t *data, size_t len,
                             uint8_t *out, size_t out_len);

#endif /* TMON_HANDLER_H */
