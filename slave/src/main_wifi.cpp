/*
 * tmon slave firmware -- WiFi protocol handler
 *
 * Connects to WiFi and master TCP server, responds to POLL requests.
 * Protocol defined in docs/protocol.org.
 * Debug output on USB serial (115200 baud).
 */

#include <Arduino.h>
#include <WiFi.h>

#include "handler.h"
#include "led.h"
#include "protocol.h"
#include "sensors.h"

/*
 * Required build flags (injected by wifi_config.py from master/config-wifi.toml):
 *   WIFI_SSID, WIFI_PASSWORD, MASTER_HOST, MASTER_PORT
 * SLAVE_ADDR is set in platformio.ini (per-device).
 */

/* Receive/transmit buffers */
static const size_t BUF_SIZE = 64;
static uint8_t rx_buf[BUF_SIZE];
static uint8_t tx_buf[BUF_SIZE];

/* TCP client */
static WiFiClient client;

/* Read timeout (ms) */
static const int READ_TIMEOUT_MS = 100;

/* Reconnect delay (ms) -- avoid hammering on connection failure */
static const unsigned long RECONNECT_DELAY_MS = 5000;
static unsigned long last_connect_attempt = 0;

/* Watchdog timeout (ms) -- LED turns red if no POLL received */
static const uint32_t WATCHDOG_TIMEOUT_MS = 90000;

/* WiFi state tracking for LED */
static bool wifi_was_connected = false;

static bool
ensure_connected (void)
{
  if (client.connected ())
    return true;

  /* Rate-limit connection attempts */
  unsigned long now = millis ();
  if (now - last_connect_attempt < RECONNECT_DELAY_MS)
    return false;
  last_connect_attempt = now;

  /* Ensure WiFi is up */
  if (WiFi.status () != WL_CONNECTED)
    {
      Serial.println ("Connecting to WiFi...");
      WiFi.begin (WIFI_SSID, WIFI_PASSWORD);
      return false;  /* Check again next loop */
    }

  /* Connect to master */
  Serial.println ("Connecting to master...");
  if (!client.connect (MASTER_HOST, MASTER_PORT))
    return false;

  client.write ((uint8_t) SLAVE_ADDR);
  Serial.println ("Connected");
  return true;
}

void
setup (void)
{
  Serial.begin (115200);
  delay (1000);

  Serial.println ("tmon WiFi slave starting");
  Serial.print ("Address: ");
  Serial.println (SLAVE_ADDR);

  tmon_sensors_init ();
  led_init (WATCHDOG_TIMEOUT_MS);
  WiFi.begin (WIFI_SSID, WIFI_PASSWORD);
}

void
loop (void)
{
  unsigned long now = millis ();

  /* Track WiFi state changes for LED */
  bool wifi_connected = (WiFi.status () == WL_CONNECTED);
  if (wifi_connected && !wifi_was_connected)
    led_notify_wifi_connected ();
  else if (!wifi_connected && wifi_was_connected)
    led_notify_wifi_disconnected ();
  wifi_was_connected = wifi_connected;

  if (!ensure_connected ())
    {
      led_update (now);
      return;
    }

  /* Read frame header (4 bytes: START, ADDR, CMD, LEN) */
  client.setTimeout (READ_TIMEOUT_MS);
  size_t rx_len = client.readBytes (rx_buf, TMON_FRAME_OVERHEAD - 2);
  if (rx_len < 4)
    return;  /* Timeout or partial read */

  /* Read payload + CRC based on LEN field */
  uint8_t payload_len = rx_buf[3];
  size_t remaining = payload_len + 2;  /* payload + CRC */
  if (remaining > 0 && remaining <= BUF_SIZE - 4)
    {
      size_t got = client.readBytes (&rx_buf[4], remaining);
      if (got < remaining)
        return;  /* Incomplete frame, discard */
      rx_len += got;
    }

  /* Process frame and send response */
  size_t tx_len = tmon_handler_process (SLAVE_ADDR, rx_buf, rx_len,
                                        tx_buf, BUF_SIZE);
  if (tx_len > 0)
    {
      client.write (tx_buf, tx_len);
      led_notify_poll ();
    }

  led_update (now);
}
