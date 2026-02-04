/*
 * protocol.c -- tmon RS-485 frame encoding/decoding
 *
 * Implements the binary framing format described in docs/protocol.org.
 */

#include "protocol.h"

#include <string.h>

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
tmon_crc16 (const uint8_t *data, size_t len)
{
  uint16_t crc = 0xFFFF;
  size_t i;

  for (i = 0; i < len; i++)
    {
      int bit;
      crc ^= data[i];
      for (bit = 0; bit < 8; bit++)
        {
          if (crc & 0x0001)
            crc = (crc >> 1) ^ 0xA001;
          else
            crc >>= 1;
        }
    }
  return crc;
}

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
                     const uint8_t *payload, uint8_t payload_len)
{
  size_t frame_len;
  size_t pos;
  uint16_t crc;

  if (addr < 1 || addr > 247)
    return 0;

  frame_len = TMON_FRAME_OVERHEAD + payload_len;
  if (buf_len < frame_len)
    return 0;

  buf[0] = TMON_START_BYTE;
  buf[1] = addr;
  buf[2] = cmd;
  buf[3] = payload_len;

  if (payload_len > 0 && payload != NULL)
    memcpy (&buf[4], payload, payload_len);

  /* CRC over ADDR + CMD + LEN + PAYLOAD */
  crc = tmon_crc16 (&buf[1], 3 + payload_len);

  pos = 4 + payload_len;
  buf[pos]     = (uint8_t)(crc & 0xFF);
  buf[pos + 1] = (uint8_t)(crc >> 8);

  return frame_len;
}

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
                   uint8_t *payload_len)
{
  uint8_t plen;
  size_t expected_len;
  uint16_t crc_received;
  uint16_t crc_computed;

  if (len < TMON_FRAME_OVERHEAD)
    return -1;

  if (data[0] != TMON_START_BYTE)
    return -1;

  plen = data[3];
  expected_len = TMON_FRAME_OVERHEAD + plen;
  if (len != expected_len)
    return -1;

  /* CRC is stored LE at the end of the frame */
  crc_received = (uint16_t)data[4 + plen]
               | ((uint16_t)data[4 + plen + 1] << 8);
  crc_computed = tmon_crc16 (&data[1], 3 + plen);
  if (crc_received != crc_computed)
    return -1;

  if (data[1] < 1 || data[1] > 247)
    return -1;

  *addr = data[1];
  *cmd = data[2];
  *payload_len = plen;
  if (plen > 0)
    *payload = &data[4];
  else
    *payload = NULL;

  return 0;
}

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
                  struct tmon_reply_payload *out)
{
  int i;

  if (payload_len != TMON_REPLY_PAYLOAD_LEN)
    return -1;

  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      size_t offset = i * 2;
      out->temps[i] = (int16_t)((uint16_t)payload[offset]
                     | ((uint16_t)payload[offset + 1] << 8));
    }
  return 0;
}
