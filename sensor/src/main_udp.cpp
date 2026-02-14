/*
 * tmon sensor firmware -- UDP push with always-on WiFi
 *
 * Stays connected to WiFi and pushes temperature readings periodically.
 * Blinks red on WiFi failure; blinks green after each send.
 * Boot button (GPIO 0) blinks yellow N times (N = config_sensor_addr).
 *
 * Protocol defined in docs/protocol.org.
 * Debug output on USB serial (115200 baud).
 *
 * Per-device configuration (address, WiFi credentials, server host/port)
 * is patched into the binary by deploy/tmon-patch.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#include "config.h"
#include "handler.h"
#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* Boot button (active LOW, internal pull-up) */
static const int BOOT_BUTTON = 0;

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
  /* USB serial for debug output */
  Serial.begin (115200);
  /* Wait enough to attach screen to the serial log.  */
  delay (5000);

  config_init ();

  tmon_sensors_init ();
  led_init ();

  pinMode (BOOT_BUTTON, INPUT_PULLUP);

  Serial.println ("tmon UDP push sensor starting");
  Serial.print ("Address: ");
  Serial.println (config_sensor_addr);
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
  size_t tx_len = tmon_build_reply (tx_buf, BUF_SIZE, config_sensor_addr);
  if (tx_len > 0)
    {
      struct tmon_reply_payload parsed;
      tmon_parse_reply (&tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
      Serial.print ("Sending REPLY: ");
      Serial.print (tx_len);
      Serial.print (" bytes, ");
      log_temps (parsed.temps);

      udp.beginPacket (config_host, config_server_port);
      udp.write (tx_buf, tx_len);
      udp.endPacket ();
      led_tx_blink ();
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
      if (digitalRead (BOOT_BUTTON) == LOW
          && (now - last_button_ms) >= 500)
        {
          last_button_ms = now;
          led_identify (config_sensor_addr);
          Serial.print ("Identify: blinking ");
          Serial.print (config_sensor_addr);
          Serial.println (" times");
        }

      delay (TICK_MS);
    }
}
