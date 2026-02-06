/*
 * test_handler.c -- Unity tests for tmon message handler.
 *
 * Tests protocol request/response logic using stub sensors.
 * Run with: pio test -e native
 */

#include <string.h>
#include <unity.h>

#include "handler.h"
#include "protocol.h"

/* External test helper from sensors_stub.c */
extern void tmon_sensors_stub_set (int16_t t0, int16_t t1, int16_t t2,
                                   int16_t t3);

/* -- Handler tests -------------------------------------------------------- */

void
test_handler_responds_to_poll (void)
{
  /* Valid POLL for our address should generate a REPLY. */
  uint8_t poll[6];
  uint8_t reply[64];
  size_t poll_len, reply_len;

  tmon_sensors_stub_set (235, 198, TMON_TEMP_INVALID, TMON_TEMP_INVALID);

  poll_len = tmon_encode_frame (poll, sizeof (poll), 3, TMON_CMD_POLL,
                                  NULL, 0);
  reply_len = tmon_handler_process (3, poll, poll_len, reply, sizeof (reply));

  /* Should get a 14-byte REPLY frame */
  TEST_ASSERT_EQUAL (14, reply_len);

  /* Decode and verify */
  uint8_t addr, cmd, plen;
  const uint8_t *payload;
  int rc = tmon_decode_frame (reply, reply_len, &addr, &cmd, &payload, &plen);
  TEST_ASSERT_EQUAL (0, rc);
  TEST_ASSERT_EQUAL (3, addr);
  TEST_ASSERT_EQUAL (TMON_CMD_REPLY, cmd);
  TEST_ASSERT_EQUAL (8, plen);

  /* Parse temperatures */
  struct tmon_reply_payload rp;
  TEST_ASSERT_EQUAL (0, tmon_parse_reply (payload, plen, &rp));
  TEST_ASSERT_EQUAL_INT16 (235, rp.temps[0]);
  TEST_ASSERT_EQUAL_INT16 (198, rp.temps[1]);
  TEST_ASSERT_EQUAL_INT16 ((int16_t)TMON_TEMP_INVALID, rp.temps[2]);
  TEST_ASSERT_EQUAL_INT16 ((int16_t)TMON_TEMP_INVALID, rp.temps[3]);
}

void
test_handler_ignores_wrong_address (void)
{
  /* POLL for different address should not generate a response. */
  uint8_t poll[6];
  uint8_t reply[64];
  size_t poll_len, reply_len;

  poll_len = tmon_encode_frame (poll, sizeof (poll), 5, TMON_CMD_POLL,
                                  NULL, 0);
  reply_len = tmon_handler_process (3, poll, poll_len, reply, sizeof (reply));

  TEST_ASSERT_EQUAL (0, reply_len);
}

void
test_handler_ignores_non_poll (void)
{
  /* REPLY command should not generate a response. */
  uint8_t frame[14];
  uint8_t reply[64];
  uint8_t payload[] = {0, 0, 0, 0, 0, 0, 0, 0};
  size_t frame_len, reply_len;

  frame_len = tmon_encode_frame (frame, sizeof (frame), 3, TMON_CMD_REPLY,
                                   payload, sizeof (payload));
  reply_len = tmon_handler_process (3, frame, frame_len, reply, sizeof (reply));

  TEST_ASSERT_EQUAL (0, reply_len);
}

void
test_handler_ignores_invalid_frame (void)
{
  /* Malformed frame should not generate a response. */
  uint8_t garbage[] = {0x99, 0x03, 0x01, 0x00, 0x00, 0x00};
  uint8_t reply[64];
  size_t reply_len;

  reply_len = tmon_handler_process (3, garbage, sizeof (garbage),
                                    reply, sizeof (reply));

  TEST_ASSERT_EQUAL (0, reply_len);
}

void
test_handler_ignores_short_frame (void)
{
  /* Frame shorter than minimum should not crash or respond. */
  uint8_t short_data[] = {0x01, 0x03};
  uint8_t reply[64];
  size_t reply_len;

  reply_len = tmon_handler_process (3, short_data, sizeof (short_data),
                                    reply, sizeof (reply));

  TEST_ASSERT_EQUAL (0, reply_len);
}

void
test_handler_ignores_bad_crc (void)
{
  /* Frame with bad CRC should not generate a response. */
  uint8_t poll[6];
  uint8_t reply[64];
  size_t poll_len, reply_len;

  poll_len = tmon_encode_frame (poll, sizeof (poll), 3, TMON_CMD_POLL,
                                  NULL, 0);
  poll[5] ^= 0xFF;  /* Corrupt CRC */

  reply_len = tmon_handler_process (3, poll, poll_len, reply, sizeof (reply));

  TEST_ASSERT_EQUAL (0, reply_len);
}

void
test_handler_different_temps (void)
{
  /* Verify handler returns whatever sensors report. */
  uint8_t poll[6];
  uint8_t reply[64];
  size_t poll_len, reply_len;

  tmon_sensors_stub_set (100, -50, 0, 325);

  poll_len = tmon_encode_frame (poll, sizeof (poll), 1, TMON_CMD_POLL,
                                  NULL, 0);
  reply_len = tmon_handler_process (1, poll, poll_len, reply, sizeof (reply));

  TEST_ASSERT_EQUAL (14, reply_len);

  uint8_t addr, cmd, plen;
  const uint8_t *payload;
  tmon_decode_frame (reply, reply_len, &addr, &cmd, &payload, &plen);

  struct tmon_reply_payload rp;
  tmon_parse_reply (payload, plen, &rp);
  TEST_ASSERT_EQUAL_INT16 (100, rp.temps[0]);
  TEST_ASSERT_EQUAL_INT16 (-50, rp.temps[1]);
  TEST_ASSERT_EQUAL_INT16 (0, rp.temps[2]);
  TEST_ASSERT_EQUAL_INT16 (325, rp.temps[3]);
}

/* -- Unity setup/teardown ------------------------------------------------- */

void
setUp (void)
{
  /* Reset stub temps before each test */
  tmon_sensors_stub_set (0, 0, 0, 0);
}

void
tearDown (void)
{
}

int
main (void)
{
  UNITY_BEGIN ();

  RUN_TEST (test_handler_responds_to_poll);
  RUN_TEST (test_handler_ignores_wrong_address);
  RUN_TEST (test_handler_ignores_non_poll);
  RUN_TEST (test_handler_ignores_invalid_frame);
  RUN_TEST (test_handler_ignores_short_frame);
  RUN_TEST (test_handler_ignores_bad_crc);
  RUN_TEST (test_handler_different_temps);

  return UNITY_END ();
}
