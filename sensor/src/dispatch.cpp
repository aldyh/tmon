/*
 * dispatch.cpp -- Frame dispatch for tmon sensor
 *
 * Dispatches incoming POLL requests and builds REPLY responses.
 */

#include "dispatch.h"
#include "protocol.h"
#include "sensors.h"

/*
 * tmon_build_reply_frame -- Build a REPLY frame with current temperatures.
 *
 * Reads the current sensor temperatures, packs them into a REPLY
 * payload, and encodes the complete frame.
 *
 * Args:
 *   buf:      Output buffer for the frame.
 *   buf_len:  Size of the output buffer in bytes.
 *   addr:     Sensor address (1-247).
 *
 * Returns:
 *   Frame length written to buf, or 0 on error.
 */
size_t
tmon_build_reply_frame (uint8_t *buf, size_t buf_len, uint8_t addr)
{
  int16_t temps[TMON_NUM_CHANNELS];
  uint8_t payload[TMON_REPLY_PAYLOAD_LEN];

  tmon_sensor_read_temps (temps);
  tmon_proto_build_reply_payload (payload, temps);
  return tmon_proto_encode_frame (buf, buf_len, addr, TMON_CMD_REPLY,
                            payload, TMON_REPLY_PAYLOAD_LEN);
}

/*
 * tmon_dispatch_frame -- Dispatch a received frame and build a response.
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
 */
size_t
tmon_dispatch_frame (uint8_t my_addr, const uint8_t *data, size_t len,
                     uint8_t *out, size_t out_len)
{
  uint8_t addr, cmd, payload_len;
  const uint8_t *payload;

  /* Try to decode the frame */
  if (tmon_proto_decode_frame (data, len, &addr, &cmd, &payload, &payload_len) != 0)
    return 0;

  /* Ignore if not for us */
  if (addr != my_addr)
    return 0;

  /* Only respond to POLL */
  if (cmd != TMON_CMD_POLL)
    return 0;

  return tmon_build_reply_frame (out, out_len, my_addr);
}
