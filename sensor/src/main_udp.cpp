/*
 * tmon sensor firmware -- UDP push transport
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

#include "app.h"
#include "config.h"
#include "led.h"

/* WiFi connection timeout (ms) */
static const unsigned long WIFI_TIMEOUT_MS = 10000;

/* Polling tick interval (ms) */
static const unsigned long TICK_MS = 10;

class UDPSensor : public SensorApp
{
  WiFiUDP m_udp;

  void connect_wifi ();
  void on_init () override;
  void on_loop () override;
};

void
UDPSensor::connect_wifi ()
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
UDPSensor::on_init ()
{
  Serial.println ("tmon UDP push sensor starting");
  Serial.print ("Address: ");
  Serial.println (config_sensor_addr);
  Serial.print ("Push interval: ");
  Serial.print (config_push_interval);
  Serial.println ("s");

  connect_wifi ();
}

void
UDPSensor::on_loop ()
{
  /* Reconnect if WiFi dropped */
  if (WiFi.status () != WL_CONNECTED)
    connect_wifi ();

  /* Build and push temperature readings */
  size_t tx_len = build_reply_frame (config_sensor_addr);
  if (tx_len > 0)
    {
      log_temps ("Pushing readings: ", tx_len);
      m_udp.beginPacket (config_host, config_server_port);
      m_udp.write (m_tx_buf, tx_len);
      m_udp.endPacket ();
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
      check_button ();
      delay (TICK_MS);
    }
}

static UDPSensor sensor;

void
setup (void)
{
  sensor.setup ();
}

void
loop (void)
{
  sensor.loop ();
}
