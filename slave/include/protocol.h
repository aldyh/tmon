/*
 * protocol.h -- tmon RS-485 frame encoding/decoding
 *
 * Binary framing as described in docs/protocol.org.
 * Shared between slave firmware modules.
 */

#ifndef TMON_PROTOCOL_H
#define TMON_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

/* Frame delimiter */
#define TMON_START_BYTE  0x01

/* Command bytes */
#define TMON_CMD_POLL   0x01
#define TMON_CMD_REPLY  0x02

/* Maximum payload length */
#define TMON_MAX_PAYLOAD  255

/* REPLY payload is exactly 8 bytes (4 x int16_t) */
#define TMON_REPLY_PAYLOAD_LEN  8

/* Sentinel value for invalid/unconnected temperature channels */
#define TMON_TEMP_INVALID  0x7FFF

/* Frame overhead: START + ADDR + CMD + LEN + CRC_LO + CRC_HI */
#define TMON_FRAME_OVERHEAD  6

/* Number of temperature channels per slave */
#define TMON_NUM_CHANNELS  4

/*
 * Parsed REPLY payload: four temperature readings.
 * Temperatures are signed, in tenths of a degree Celsius.
 * Invalid channels have the value TMON_TEMP_INVALID (0x7FFF).
 */
struct tmon_reply_payload
{
  int16_t temps[TMON_NUM_CHANNELS];
};

/*
 * tmon_crc16 -- Compute CRC-16/MODBUS over a byte buffer.
 *
 * Uses polynomial 0x8005 with initial value 0xFFFF and reflected
 * input/output (standard MODBUS CRC).
 *
 * Args:
 *   data: Pointer to the input bytes.
 *   len:  Number of bytes to process.
 *
 * Returns:
 *   16-bit CRC value.
 *
 * Example:
 *   uint8_t body[] = {0x03, 0x01, 0x00};
 *   uint16_t crc = tmon_crc16 (body, 3);  // => 0x5080
 */
uint16_t
tmon_crc16 (const uint8_t *data, size_t len);

/*
 * tmon_encode_request -- Build a complete protocol frame into buf.
 *
 * Constructs: START + ADDR + CMD + LEN + PAYLOAD + CRC_LO + CRC_HI.
 * CRC is computed over ADDR + CMD + LEN + PAYLOAD.
 *
 * Args:
 *   buf:         Output buffer (caller-provided).
 *   buf_len:     Size of the output buffer in bytes.
 *   addr:        Slave address (1-247).
 *   cmd:         Command byte.
 *   payload:     Payload bytes (may be NULL when payload_len is 0).
 *   payload_len: Number of payload bytes.
 *
 * Returns:
 *   Frame length written to buf, or 0 on error (bad addr, buffer too small).
 *
 * Example:
 *   uint8_t buf[64];
 *   size_t n = tmon_encode_request (buf, sizeof (buf), 3, TMON_CMD_POLL,
 *                                   NULL, 0);
 *   // buf[0..5] = {0x01, 0x03, 0x01, 0x00, 0x80, 0x50}, n = 6
 */
size_t
tmon_encode_request (uint8_t *buf, size_t buf_len, uint8_t addr, uint8_t cmd,
                     const uint8_t *payload, uint8_t payload_len);

/*
 * tmon_decode_frame -- Decode a raw frame and extract fields.
 *
 * Validates START byte, length field, CRC, and address range.
 * On success the payload pointer points into the input data buffer
 * (zero-copy).
 *
 * Args:
 *   data:        Raw frame bytes.
 *   len:         Number of bytes in data.
 *   addr:        Output: slave address.
 *   cmd:         Output: command byte.
 *   payload:     Output: pointer into data at the payload start.
 *   payload_len: Output: payload length.
 *
 * Returns:
 *   0 on success, -1 on any validation failure.
 *
 * Example:
 *   uint8_t raw[] = {0x01, 0x03, 0x01, 0x00, 0x80, 0x50};
 *   uint8_t addr, cmd, plen;
 *   const uint8_t *payload;
 *   int rc = tmon_decode_frame (raw, 6, &addr, &cmd, &payload, &plen);
 *   // rc = 0, addr = 3, cmd = 1, plen = 0
 */
int
tmon_decode_frame (const uint8_t *data, size_t len, uint8_t *addr,
                   uint8_t *cmd, const uint8_t **payload,
                   uint8_t *payload_len);

/*
 * tmon_parse_reply -- Parse an 8-byte REPLY payload.
 *
 * Unpacks four int16-LE temperature values into a tmon_reply_payload
 * struct.  Invalid channels have the value TMON_TEMP_INVALID.
 *
 * Args:
 *   payload:     Pointer to the 8-byte payload.
 *   payload_len: Must be TMON_REPLY_PAYLOAD_LEN (8).
 *   out:         Output struct to fill.
 *
 * Returns:
 *   0 on success, -1 if payload_len != 8.
 *
 * Example:
 *   uint8_t pl[] = {0xEB,0x00, 0xC6,0x00, 0xFF,0x7F, 0xFF,0x7F};
 *   struct tmon_reply_payload rp;
 *   int rc = tmon_parse_reply (pl, 8, &rp);
 *   // rc = 0, rp.temps = {235, 198, 32767, 32767}
 */
int
tmon_parse_reply (const uint8_t *payload, uint8_t payload_len,
                  struct tmon_reply_payload *out);

#endif /* TMON_PROTOCOL_H */
