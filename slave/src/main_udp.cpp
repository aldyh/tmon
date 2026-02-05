/*
 * tmon slave firmware -- UDP push with deep sleep
 *
 * Wakes periodically, connects to WiFi, pushes temperature reading
 * via UDP, then returns to deep sleep.
 *
 * Protocol defined in docs/protocol.org.
 * Debug output on USB serial (115200 baud).
 *
 * Build flags (injected by wifi_config.py from master/*.toml):
 *   WIFI_SSID, WIFI_PASSWORD, MASTER_HOST (from wifi.toml)
 *   MASTER_PORT, PUSH_INTERVAL_S (from config-udp.toml [udp] section)
 *   SLAVE_ADDR (from environment or platformio.ini)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* PUSH_INTERVAL_S must be set via build flag (from config-udp.toml) */
#ifndef PUSH_INTERVAL_S
#error "PUSH_INTERVAL_S not defined -- check config-udp.toml"
#endif

/* WiFi connection timeout (ms) */
static const unsigned long WIFI_TIMEOUT_MS = 15000;

/* Transmit buffer */
static const size_t BUF_SIZE = 64;
static uint8_t tx_buf[BUF_SIZE];

/* UDP client */
static WiFiUDP udp;

/*
 * Build a REPLY frame with current temperatures.
 * Returns frame length.
 */
static size_t
build_reply_frame (uint8_t *buf, size_t buf_len)
{
  int16_t temps[TMON_NUM_CHANNELS];
  uint8_t payload[TMON_REPLY_PAYLOAD_LEN];

  /* Read temperatures */
  tmon_read_temps (temps);

  /* Build payload: 4 x int16-LE */
  for (int i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      payload[i * 2]     = (uint8_t) (temps[i] & 0xFF);
      payload[i * 2 + 1] = (uint8_t) ((temps[i] >> 8) & 0xFF);
    }

  /* Encode the REPLY frame */
  return tmon_encode_request (buf, buf_len, SLAVE_ADDR, TMON_CMD_REPLY,
                              payload, TMON_REPLY_PAYLOAD_LEN);
}

/*
 * Connect to WiFi with timeout.
 * Returns true on success.
 */
static bool
connect_wifi (void)
{
  Serial.println ("Connecting to WiFi...");
  WiFi.begin (WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis ();
  while (WiFi.status () != WL_CONNECTED)
    {
      if (millis () - start > WIFI_TIMEOUT_MS)
        {
          Serial.println ("WiFi timeout");
          return false;
        }
      led_update (millis ());
      delay (100);
    }

  Serial.print ("WiFi connected, IP: ");
  Serial.println (WiFi.localIP ());
  return true;
}

/*
 * Send reading via UDP and go to deep sleep.
 */
static void
send_and_sleep (void)
{
  /* Build REPLY frame */
  size_t tx_len = build_reply_frame (tx_buf, BUF_SIZE);
  if (tx_len == 0)
    {
      Serial.println ("Failed to build frame");
      return;
    }

  /* Log what we're sending */
  struct tmon_reply_payload parsed;
  tmon_parse_reply (&tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
  Serial.print ("Sending REPLY: ");
  Serial.print (tx_len);
  Serial.print (" bytes, ");
  log_temps (parsed.temps);

  /* Send UDP packet */
  udp.beginPacket (MASTER_HOST, MASTER_PORT);
  udp.write (tx_buf, tx_len);
  udp.endPacket ();

  /* Brief green flash to indicate success */
  led_blink ();
  led_update (millis ());
  delay (200);

  Serial.print ("Sleeping for ");
  Serial.print (PUSH_INTERVAL_S);
  Serial.println (" seconds");
  Serial.flush ();

  /* Enter deep sleep */
  esp_sleep_enable_timer_wakeup ((uint64_t) PUSH_INTERVAL_S * 1000000ULL);
  esp_deep_sleep_start ();
}

void
setup (void)
{
  /* No watchdog needed -- we go to sleep after sending */
  led_init (0);
  Serial.begin (115200);

  Serial.println ("tmon UDP push slave starting");
  Serial.print ("Address: ");
  Serial.println (SLAVE_ADDR);
  Serial.print ("Push interval: ");
  Serial.print (PUSH_INTERVAL_S);
  Serial.println ("s");

  tmon_sensors_init ();

  /* Connect to WiFi, retrying until successful */
  while (!connect_wifi ())
    {
      led_error ();
      led_update (millis ());
      Serial.println ("WiFi failed, retrying in 60s");
      delay (60000);
    }

  /* Send reading and sleep */
  send_and_sleep ();
}

void
loop (void)
{
  /* Never reached -- we deep sleep in setup() */
}
