/*
 * protocol.h -- tmon RS-485 frame encoding/decoding
 *
 * Binary framing as described in docs/protocol.org.
 * Shared between client firmware modules.
 */

#ifndef TMON_PROTOCOL_H
#define TMON_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

/* Command bytes */
#define TMON_CMD_POLL   0x01
#define TMON_CMD_REPLY  0x02

/* REPLY payload is exactly 8 bytes (4 x int16_t) */
#define TMON_REPLY_PAYLOAD_LEN  8

/* Sentinel value for invalid/unconnected temperature channels */
#define TMON_TEMP_INVALID  0x7FFF

/* Number of temperature channels per client */
#define TMON_NUM_CHANNELS  4

/*
 * Parsed REPLY payload: four temperature readings.
 * Temperatures are signed, in tenths of a degree Celsius.
 * Invalid channels have the value TMON_TEMP_INVALID (0x7FFF).
 */
struct tmon_proto_reply_payload
{
  int16_t temps[TMON_NUM_CHANNELS];
};

size_t tmon_proto_encode_frame (uint8_t *buf, size_t buf_len, uint8_t addr,
                            uint8_t cmd, const uint8_t *payload,
                            uint8_t payload_len);

int tmon_proto_decode_frame (const uint8_t *data, size_t len, uint8_t *addr,
                       uint8_t *cmd, const uint8_t **payload,
                       uint8_t *payload_len);

void tmon_proto_build_reply_payload (uint8_t *payload,
                               const int16_t *temps);

int tmon_proto_parse_reply (const uint8_t *payload, uint8_t payload_len,
                      struct tmon_proto_reply_payload *out);

#endif /* TMON_PROTOCOL_H */
