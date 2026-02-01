/*
 * protocol.h -- tmon RS-485 frame encoding/decoding
 *
 * Binary framing as described in docs/protocol.md.
 * Shared between slave firmware modules.
 */

#ifndef TMON_PROTOCOL_H
#define TMON_PROTOCOL_H

#include <stdint.h>

/* Frame delimiter */
#define TMON_START_BYTE  0x01

/* Command bytes */
#define TMON_CMD_POLL_REQUEST   0x10
#define TMON_CMD_POLL_RESPONSE  0x11

/* Maximum payload length */
#define TMON_MAX_PAYLOAD  255

#endif /* TMON_PROTOCOL_H */
