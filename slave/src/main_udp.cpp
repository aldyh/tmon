/*
 * tmon slave firmware -- UDP push with always-on WiFi
 *
 * Stays connected to WiFi and pushes temperature readings periodically.
 * Blinks red on WiFi failure; LED off when connected.
 * Boot button (GPIO 0) blinks yellow N times (N = config_slave_addr).
 *
 * Protocol defined in docs/protocol.org.
 * Debug output on USB serial (115200 baud).
 *
 * Per-device configuration (address, WiFi credentials, master host/port)
 * is patched into the binary by deploy/tmon-patch.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "config.h"
#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* Boot button (active LOW, internal pull-up) */
static const int PIN_BUTTON = 0;
static const unsigned long BUTTON_DEBOUNCE_MS = 500;

/* WiFi connection timeout (ms) */
static const unsigned long WIFI_TIMEOUT_MS = 10000;

/* Polling tick interval (ms) */
static const unsigned long TICK_MS = 10;

/* Transmit buffer */
static const size_t BUF_SIZE = 64;
static uint8_t tx_buf[BUF_SIZE];

/* UDP client */
static WiFiUDP udp;

/* Button state */
static unsigned long last_button_ms = 0;

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
  return tmon_encode_frame (buf, buf_len, config_slave_addr, TMON_CMD_REPLY,
                              payload, TMON_REPLY_PAYLOAD_LEN);
}

/*
 * Connect to WiFi, retrying until successful.
 * Blinks red on each failed attempt.
 */
static void
connect_wifi (void)
{
  for (;;)
    {
      Serial.println ("Connecting to WiFi...");
      WiFi.begin (config_ssid, config_pass);

      unsigned long start = millis ();
      while (WiFi.status () != WL_CONNECTED)
        {
          if (millis () - start > WIFI_TIMEOUT_MS)
            break;
          delay (100);
        }

      if (WiFi.status () == WL_CONNECTED)
        {
          Serial.print ("WiFi connected, IP: ");
          Serial.println (WiFi.localIP ());
          return;
        }

      Serial.println ("WiFi timeout, retrying...");
      led_error_blink (3);
    }
}

void
setup (void)
{
  Serial.begin (115200);

  config_init ();

  tmon_sensors_init ();
  led_init ();

  pinMode (PIN_BUTTON, INPUT_PULLUP);

  Serial.println ("tmon UDP push slave starting");
  Serial.print ("Address: ");
  Serial.println (config_slave_addr);
  Serial.print ("Push interval: ");
  Serial.print (config_push_interval);
  Serial.println ("s");

  connect_wifi ();
}

void
loop (void)
{
  /* Reconnect if WiFi dropped */
  if (WiFi.status () != WL_CONNECTED)
    connect_wifi ();

  /* Build and send REPLY frame */
  size_t tx_len = build_reply_frame (tx_buf, BUF_SIZE);
  if (tx_len > 0)
    {
      struct tmon_reply_payload parsed;
      tmon_parse_reply (&tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
      Serial.print ("Sending REPLY: ");
      Serial.print (tx_len);
      Serial.print (" bytes, ");
      log_temps (parsed.temps);

      udp.beginPacket (config_host, config_master_port);
      udp.write (tx_buf, tx_len);
      udp.endPacket ();
    }
  else
    {
      Serial.println ("Failed to build frame");
    }

  /* Wait for push interval, polling button */
  unsigned long wait_start = millis ();
  while (millis () - wait_start < config_push_interval * 1000UL)
    {
      unsigned long now = millis ();

      /* Check boot button (active LOW) */
      if (digitalRead (PIN_BUTTON) == LOW
          && (now - last_button_ms) >= BUTTON_DEBOUNCE_MS)
        {
          last_button_ms = now;
          led_identify (config_slave_addr);
          Serial.print ("Identify: blinking ");
          Serial.print (config_slave_addr);
          Serial.println (" times");
        }

      delay (TICK_MS);
    }
}
