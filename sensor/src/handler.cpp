/*
 * handler.c -- Protocol message handler for tmon sensor
 *
 * Processes incoming POLL requests and builds REPLY responses.
 */

#include "handler.h"
#include "protocol.h"
#include "sensors.h"

/*
 * tmon_handler_process -- Process a received frame and build a response.
 *
 * If the frame is a valid POLL for our address, builds a REPLY with
 * current temperature readings.  Otherwise returns 0.
 *
 * Args:
 *   my_addr:  This sensor's address (1-247).
 *   data:     Raw received frame bytes.
 *   len:      Number of bytes in data.
 *   out:      Output buffer for response frame.
 *   out_len:  Size of output buffer.
 *
 * Returns:
 *   Length of response written to out, or 0 if no response needed.
 *
 * Example:
 *   uint8_t rx[64], tx[64];
 *   size_t rx_len = read_from_bus (rx, sizeof (rx));
 *   size_t tx_len = tmon_handler_process (3, rx, rx_len, tx, sizeof (tx));
 *   if (tx_len > 0)
 *     write_to_bus (tx, tx_len);
 */
size_t
tmon_handler_process (uint8_t my_addr, const uint8_t *data, size_t len,
                      uint8_t *out, size_t out_len)
{
  uint8_t addr, cmd, payload_len;
  const uint8_t *payload;
  int16_t temps[TMON_NUM_CHANNELS];
  uint8_t reply_payload[TMON_REPLY_PAYLOAD_LEN];
  int i;

  /* Try to decode the frame */
  if (tmon_decode_frame (data, len, &addr, &cmd, &payload, &payload_len) != 0)
    return 0;

  /* Ignore if not for us */
  if (addr != my_addr)
    return 0;

  /* Only respond to POLL */
  if (cmd != TMON_CMD_POLL)
    return 0;

  /* Read temperatures from sensors */
  tmon_read_temps (temps);

  /* Build reply payload: 4 x int16-LE */
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      reply_payload[i * 2]     = (uint8_t)(temps[i] & 0xFF);
      reply_payload[i * 2 + 1] = (uint8_t)((temps[i] >> 8) & 0xFF);
    }

  /* Encode the REPLY frame */
  return tmon_encode_frame (out, out_len, my_addr, TMON_CMD_REPLY,
                              reply_payload, TMON_REPLY_PAYLOAD_LEN);
}
