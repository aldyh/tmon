/*
 * test_protocol.c -- Unity tests for tmon protocol encode/decode.
 *
 * Mirrors the Python test coverage in server/tests/test_protocol.py.
 * Run with: pio test -e native
 */

#include <string.h>
#include <unity.h>

#include "protocol.h"

/* -- encode_request tests ------------------------------------------------- */

void
test_encode_example1_poll_sensor3 (void)
{
  /* POLL for sensor 3 should produce the Example 1 frame. */
  uint8_t expected[] = {0x01, 0x03, 0x01, 0x00, 0x80, 0x50};
  uint8_t buf[64];
  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 3, TMON_CMD_POLL,
                                  NULL, 0);
  TEST_ASSERT_EQUAL (6, n);
  TEST_ASSERT_EQUAL_HEX8_ARRAY (expected, buf, 6);
}

void
test_encode_example2_reply_frame (void)
{
  /* encode_request should produce the Example 2 frame. */
  uint8_t payload[] = {
    0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
  };
  uint8_t expected[] = {
    0x01, 0x03, 0x02, 0x08,
    0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
    0x90, 0xEB,
  };
  uint8_t buf[64];
  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 3, TMON_CMD_REPLY,
                                  payload, sizeof (payload));
  TEST_ASSERT_EQUAL (14, n);
  TEST_ASSERT_EQUAL_HEX8_ARRAY (expected, buf, 14);
}

void
test_encode_poll_length_is_6 (void)
{
  /* POLL frame with no payload is always 6 bytes. */
  uint8_t buf[64];
  TEST_ASSERT_EQUAL (6, tmon_proto_encode_frame (buf, sizeof (buf), 1,
                                             TMON_CMD_POLL, NULL, 0));
  TEST_ASSERT_EQUAL (6, tmon_proto_encode_frame (buf, sizeof (buf), 247,
                                             TMON_CMD_POLL, NULL, 0));
}

void
test_encode_start_byte (void)
{
  /* First byte of any frame is the START byte (0x01). */
  uint8_t buf[64];
  tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_POLL, NULL, 0);
  TEST_ASSERT_EQUAL_HEX8 (0x01, buf[0]);
}

void
test_encode_addr_in_frame (void)
{
  /* Address appears at offset 1. */
  uint8_t buf[64];
  tmon_proto_encode_frame (buf, sizeof (buf), 42, TMON_CMD_POLL, NULL, 0);
  TEST_ASSERT_EQUAL (42, buf[1]);
}

void
test_encode_cmd_in_frame (void)
{
  /* Command byte appears at offset 2. */
  uint8_t buf[64];
  tmon_proto_encode_frame (buf, sizeof (buf), 1, 0xAB, NULL, 0);
  TEST_ASSERT_EQUAL_HEX8 (0xAB, buf[2]);
}

void
test_encode_len_field (void)
{
  /* LEN field at offset 3 reflects actual payload length. */
  uint8_t buf[64];
  uint8_t payload[] = {0x01, 0x02, 0x03};
  tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_POLL,
                       payload, sizeof (payload));
  TEST_ASSERT_EQUAL (3, buf[3]);
}

void
test_encode_addr_zero_rejected (void)
{
  /* Address 0 should be rejected (returns 0). */
  uint8_t buf[64];
  TEST_ASSERT_EQUAL (0, tmon_proto_encode_frame (buf, sizeof (buf), 0,
                                             TMON_CMD_POLL, NULL, 0));
}

void
test_encode_addr_248_rejected (void)
{
  /* Address 248 should be rejected (returns 0). */
  uint8_t buf[64];
  TEST_ASSERT_EQUAL (0, tmon_proto_encode_frame (buf, sizeof (buf), 248,
                                             TMON_CMD_POLL, NULL, 0));
}

void
test_encode_buffer_too_small (void)
{
  /* Buffer too small should return 0. */
  uint8_t buf[4];
  TEST_ASSERT_EQUAL (0, tmon_proto_encode_frame (buf, sizeof (buf), 1,
                                             TMON_CMD_POLL, NULL, 0));
}

/* -- decode_frame tests --------------------------------------------------- */

void
test_decode_roundtrip_poll (void)
{
  /* encode then decode should recover the original fields. */
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 5, TMON_CMD_POLL,
                                  NULL, 0);
  int rc = tmon_proto_decode_frame (buf, n, &addr, &cmd, &payload, &plen);
  TEST_ASSERT_EQUAL (0, rc);
  TEST_ASSERT_EQUAL (5, addr);
  TEST_ASSERT_EQUAL (TMON_CMD_POLL, cmd);
  TEST_ASSERT_EQUAL (0, plen);
  TEST_ASSERT_NULL (payload);
}

void
test_decode_roundtrip_reply (void)
{
  /* Round-trip with a non-empty payload. */
  uint8_t pl[] = {0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F};
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 10, TMON_CMD_REPLY,
                                  pl, sizeof (pl));
  int rc = tmon_proto_decode_frame (buf, n, &addr, &cmd, &payload, &plen);
  TEST_ASSERT_EQUAL (0, rc);
  TEST_ASSERT_EQUAL (10, addr);
  TEST_ASSERT_EQUAL (TMON_CMD_REPLY, cmd);
  TEST_ASSERT_EQUAL (8, plen);
  TEST_ASSERT_EQUAL_HEX8_ARRAY (pl, payload, 8);
}

void
test_decode_example1_from_spec (void)
{
  /* Decode the Example 1 frame from the protocol spec. */
  uint8_t raw[] = {0x01, 0x03, 0x01, 0x00, 0x80, 0x50};
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  int rc = tmon_proto_decode_frame (raw, sizeof (raw), &addr, &cmd,
                              &payload, &plen);
  TEST_ASSERT_EQUAL (0, rc);
  TEST_ASSERT_EQUAL (3, addr);
  TEST_ASSERT_EQUAL (TMON_CMD_POLL, cmd);
  TEST_ASSERT_EQUAL (0, plen);
}

void
test_decode_example2_from_spec (void)
{
  /* Decode the Example 2 frame from the protocol spec. */
  uint8_t raw[] = {
    0x01, 0x03, 0x02, 0x08,
    0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F,
    0x90, 0xEB,
  };
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  int rc = tmon_proto_decode_frame (raw, sizeof (raw), &addr, &cmd,
                              &payload, &plen);
  TEST_ASSERT_EQUAL (0, rc);
  TEST_ASSERT_EQUAL (3, addr);
  TEST_ASSERT_EQUAL (TMON_CMD_REPLY, cmd);
  TEST_ASSERT_EQUAL (8, plen);
}

void
test_decode_error_short_frame (void)
{
  /* Frames shorter than 6 bytes should be rejected. */
  uint8_t raw[] = {0x01, 0x02, 0x03};
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (raw, sizeof (raw), &addr, &cmd,
                                            &payload, &plen));
}

void
test_decode_error_bad_start (void)
{
  /* Non-0x01 START byte should be rejected. */
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_POLL,
                                  NULL, 0);
  buf[0] = 0xFF;
  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (buf, n, &addr, &cmd,
                                            &payload, &plen));
}

void
test_decode_error_bad_crc (void)
{
  /* Corrupted CRC should be detected. */
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_POLL,
                                  NULL, 0);
  buf[n - 1] ^= 0xFF;
  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (buf, n, &addr, &cmd,
                                            &payload, &plen));
}

void
test_decode_error_length_mismatch_too_long (void)
{
  /* Extra bytes beyond what LEN declares should be rejected. */
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  size_t n = tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_POLL,
                                  NULL, 0);
  /* Pass one extra byte */
  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (buf, n + 1, &addr, &cmd,
                                            &payload, &plen));
}

void
test_decode_error_length_mismatch_too_short (void)
{
  /* Frame truncated relative to LEN should be rejected. */
  uint8_t pl[] = {0x01, 0x02, 0x03};
  uint8_t buf[64];
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  tmon_proto_encode_frame (buf, sizeof (buf), 1, TMON_CMD_REPLY,
                       pl, sizeof (pl));
  /* Pass truncated length (6 instead of 9) */
  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (buf, 6, &addr, &cmd,
                                            &payload, &plen));
}

void
test_decode_error_addr_zero (void)
{
  /* Address 0 in a frame should be rejected.
   * Hand-crafted frame: START=0x01, addr=0, cmd=POLL, len=0, CRC=0x5070. */
  uint8_t raw[] = {0x01, 0x00, TMON_CMD_POLL, 0x00, 0x70, 0x50};
  uint8_t addr, cmd, plen;
  const uint8_t *payload;

  TEST_ASSERT_EQUAL (-1, tmon_proto_decode_frame (raw, sizeof (raw), &addr, &cmd,
                                            &payload, &plen));
}

/* -- parse_reply tests ---------------------------------------------------- */

void
test_parse_example2_payload (void)
{
  /* Parse the Example 2 payload: channels 0,1 valid, 2,3 invalid. */
  uint8_t pl[] = {0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F};
  struct tmon_proto_reply_payload rp;

  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (pl, sizeof (pl), &rp));
  TEST_ASSERT_EQUAL_INT16 (235, rp.temps[0]);
  TEST_ASSERT_EQUAL_INT16 (198, rp.temps[1]);
  TEST_ASSERT_EQUAL_INT16 ((int16_t)TMON_TEMP_INVALID, rp.temps[2]);
  TEST_ASSERT_EQUAL_INT16 ((int16_t)TMON_TEMP_INVALID, rp.temps[3]);
}

void
test_parse_all_channels_invalid (void)
{
  /* All temps are TMON_TEMP_INVALID. */
  uint8_t pl[] = {0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0x7F, 0xFF, 0x7F};
  struct tmon_proto_reply_payload rp;

  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (pl, sizeof (pl), &rp));
  int i;
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    TEST_ASSERT_EQUAL_INT16 ((int16_t)TMON_TEMP_INVALID, rp.temps[i]);
}

void
test_parse_all_channels_valid (void)
{
  /* All 4 temperatures returned. */
  /* temps: 100, -50, 0, 325 (LE) */
  uint8_t pl[] = {
    0x64, 0x00,  /* 100 */
    0xCE, 0xFF,  /* -50 */
    0x00, 0x00,  /*   0 */
    0x45, 0x01,  /* 325 */
  };
  struct tmon_proto_reply_payload rp;

  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (pl, sizeof (pl), &rp));
  TEST_ASSERT_EQUAL_INT16 (100, rp.temps[0]);
  TEST_ASSERT_EQUAL_INT16 (-50, rp.temps[1]);
  TEST_ASSERT_EQUAL_INT16 (0, rp.temps[2]);
  TEST_ASSERT_EQUAL_INT16 (325, rp.temps[3]);
}

void
test_parse_negative_temperature (void)
{
  /* Negative temperature values are handled correctly. */
  /* -100 in LE = 0x9C, 0xFF */
  uint8_t pl[] = {
    0x9C, 0xFF,  /* -100 */
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
  };
  struct tmon_proto_reply_payload rp;

  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (pl, sizeof (pl), &rp));
  TEST_ASSERT_EQUAL_INT16 (-100, rp.temps[0]);
}

void
test_parse_wrong_length_short (void)
{
  /* Payload shorter than 8 bytes should be rejected. */
  uint8_t pl[7];
  struct tmon_proto_reply_payload rp;
  memset (pl, 0, sizeof (pl));
  TEST_ASSERT_EQUAL (-1, tmon_proto_parse_reply (pl, 7, &rp));
}

void
test_parse_wrong_length_long (void)
{
  /* Payload longer than 8 bytes should be rejected. */
  uint8_t pl[9];
  struct tmon_proto_reply_payload rp;
  memset (pl, 0, sizeof (pl));
  TEST_ASSERT_EQUAL (-1, tmon_proto_parse_reply (pl, 9, &rp));
}

/* -- build_reply_payload tests --------------------------------------------- */

void
test_build_reply_roundtrip (void)
{
  /* Build payload then parse it; temps should match. */
  int16_t input[TMON_NUM_CHANNELS] = {235, 198, 0, 325};
  uint8_t payload[TMON_REPLY_PAYLOAD_LEN];
  struct tmon_proto_reply_payload parsed;
  int i;

  tmon_proto_build_reply_payload (payload, input);
  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (payload, TMON_REPLY_PAYLOAD_LEN,
                                          &parsed));
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    TEST_ASSERT_EQUAL_INT16 (input[i], parsed.temps[i]);
}

void
test_build_reply_known_values (void)
{
  /* Example 2 values: 235, 198, INVALID, INVALID -> known bytes. */
  int16_t temps[TMON_NUM_CHANNELS] = {
    235, 198, (int16_t)TMON_TEMP_INVALID, (int16_t)TMON_TEMP_INVALID
  };
  uint8_t expected[] = {
    0xEB, 0x00, 0xC6, 0x00, 0xFF, 0x7F, 0xFF, 0x7F
  };
  uint8_t payload[TMON_REPLY_PAYLOAD_LEN];

  tmon_proto_build_reply_payload (payload, temps);
  TEST_ASSERT_EQUAL_HEX8_ARRAY (expected, payload, TMON_REPLY_PAYLOAD_LEN);
}

void
test_build_reply_negative_temps (void)
{
  /* Negative values should encode correctly as two's complement LE. */
  int16_t temps[TMON_NUM_CHANNELS] = {-100, -50, -1, 0};
  uint8_t payload[TMON_REPLY_PAYLOAD_LEN];
  struct tmon_proto_reply_payload parsed;
  int i;

  tmon_proto_build_reply_payload (payload, temps);

  /* -100 = 0xFF9C -> LE: 0x9C, 0xFF */
  TEST_ASSERT_EQUAL_HEX8 (0x9C, payload[0]);
  TEST_ASSERT_EQUAL_HEX8 (0xFF, payload[1]);
  /* -50 = 0xFFCE -> LE: 0xCE, 0xFF */
  TEST_ASSERT_EQUAL_HEX8 (0xCE, payload[2]);
  TEST_ASSERT_EQUAL_HEX8 (0xFF, payload[3]);
  /* -1 = 0xFFFF -> LE: 0xFF, 0xFF */
  TEST_ASSERT_EQUAL_HEX8 (0xFF, payload[4]);
  TEST_ASSERT_EQUAL_HEX8 (0xFF, payload[5]);

  /* Roundtrip check */
  TEST_ASSERT_EQUAL (0, tmon_proto_parse_reply (payload, TMON_REPLY_PAYLOAD_LEN,
                                          &parsed));
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    TEST_ASSERT_EQUAL_INT16 (temps[i], parsed.temps[i]);
}

/* -- Unity setup/teardown ------------------------------------------------- */

void
setUp (void)
{
}

void
tearDown (void)
{
}

int
main (void)
{
  UNITY_BEGIN ();

  /* Encode */
  RUN_TEST (test_encode_example1_poll_sensor3);
  RUN_TEST (test_encode_example2_reply_frame);
  RUN_TEST (test_encode_poll_length_is_6);
  RUN_TEST (test_encode_start_byte);
  RUN_TEST (test_encode_addr_in_frame);
  RUN_TEST (test_encode_cmd_in_frame);
  RUN_TEST (test_encode_len_field);
  RUN_TEST (test_encode_addr_zero_rejected);
  RUN_TEST (test_encode_addr_248_rejected);
  RUN_TEST (test_encode_buffer_too_small);

  /* Decode */
  RUN_TEST (test_decode_roundtrip_poll);
  RUN_TEST (test_decode_roundtrip_reply);
  RUN_TEST (test_decode_example1_from_spec);
  RUN_TEST (test_decode_example2_from_spec);
  RUN_TEST (test_decode_error_short_frame);
  RUN_TEST (test_decode_error_bad_start);
  RUN_TEST (test_decode_error_bad_crc);
  RUN_TEST (test_decode_error_length_mismatch_too_long);
  RUN_TEST (test_decode_error_length_mismatch_too_short);
  RUN_TEST (test_decode_error_addr_zero);

  /* Parse reply */
  RUN_TEST (test_parse_example2_payload);
  RUN_TEST (test_parse_all_channels_invalid);
  RUN_TEST (test_parse_all_channels_valid);
  RUN_TEST (test_parse_negative_temperature);
  RUN_TEST (test_parse_wrong_length_short);
  RUN_TEST (test_parse_wrong_length_long);

  /* Build reply payload */
  RUN_TEST (test_build_reply_roundtrip);
  RUN_TEST (test_build_reply_known_values);
  RUN_TEST (test_build_reply_negative_temps);

  return UNITY_END ();
}
