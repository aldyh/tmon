/*
 * dispatch.h -- Frame dispatch for tmon client
 *
 * Dispatches incoming POLL requests and builds REPLY responses.
 * Transport-agnostic: works with UART or WiFi.
 */

#ifndef TMON_DISPATCH_H
#define TMON_DISPATCH_H

#include <stddef.h>
#include <stdint.h>

size_t tmon_build_reply_frame (uint8_t *buf, size_t buf_len, uint8_t addr);

size_t tmon_dispatch_frame (uint8_t my_addr, const uint8_t *data, size_t len,
                            uint8_t *out, size_t out_len);

#endif /* TMON_DISPATCH_H */
