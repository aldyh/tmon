/*
 * protocol.c -- tmon RS-485 frame encoding/decoding
 *
 * Implements the binary framing format described in docs/protocol.md.
 */

#include "protocol.h"

#include <string.h>

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

int
tmon_parse_reply_payload (const uint8_t *payload, uint8_t payload_len,
                          struct tmon_reply_payload *out)
{
  int i;

  if (payload_len != TMON_REPLY_PAYLOAD_LEN)
    return -1;

  out->status = payload[0];
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      size_t offset = 1 + i * 2;
      out->temps[i] = (int16_t)((uint16_t)payload[offset]
                     | ((uint16_t)payload[offset + 1] << 8));
    }
  return 0;
}
