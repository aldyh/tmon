/*
 * app.cpp -- Sensor application base class
 *
 * Shared setup/loop skeleton and helpers used by all transports.
 */

#include "app.h"

#include <Arduino.h>

#include "config.h"
#include "dispatch.h"
#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* Build a REPLY frame into tx_buf. */
size_t
SensorApp::build_reply_frame (uint8_t addr)
{
  return tmon_build_reply_frame (m_tx_buf, BUF_SIZE, addr);
}

/* Dispatch an incoming request frame; response goes into tx_buf. */
size_t
SensorApp::dispatch_frame (uint8_t addr, const uint8_t *data, size_t len)
{
  return tmon_dispatch_frame (addr, data, len, m_tx_buf, BUF_SIZE);
}

/* Boot button (active LOW, internal pull-up) */
static const int BOOT_BUTTON = 0;

/*
 * SensorApp::setup -- Common hardware init, then transport-specific init.
 *
 * Initializes serial debug output, configuration, temperature sensors,
 * status LED, and boot button.  Subclasses add their own setup in
 * on_init().
 */
void
SensorApp::setup ()
{
  Serial.begin (115200);
  delay (5000);

  config_init ();
  tmon_sensor_init ();
  led_init ();
  pinMode (BOOT_BUTTON, INPUT_PULLUP);

  on_init ();
}

/*
 * SensorApp::loop -- Check boot button, then run subclass loop.
 */
void
SensorApp::loop ()
{
  check_button ();
  on_loop ();
}

/*
 * SensorApp::check_button -- Debounced boot-button check.
 *
 * If the boot button is pressed and at least 500 ms have elapsed since
 * the last press, blinks the LED to identify this sensor's address.
 */
void
SensorApp::check_button ()
{
  unsigned long now = millis ();
  if (digitalRead (BOOT_BUTTON) == LOW
      && (now - m_last_button_ms) >= 500)
    {
      m_last_button_ms = now;
      led_identify (config_sensor_addr);
      Serial.print ("Identify: blinking ");
      Serial.print (config_sensor_addr);
      Serial.println (" times");
    }
}

/*
 * SensorApp::log_reply -- Log a REPLY frame's temperatures to serial.
 *
 * Parses the payload from tx_buf and prints a labelled summary.
 * Call after building a frame into tx_buf.
 *
 * Args:
 *   label: Prefix string (e.g. "TX REPLY: " or "Sending REPLY: ").
 *   len:   Frame length in bytes.
 */
void
SensorApp::log_reply (const char *label, size_t len)
{
  struct tmon_proto_reply_payload parsed;
  tmon_proto_parse_reply (&m_tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
  Serial.print (label);
  Serial.print (len);
  Serial.print (" bytes, ");
  log_temps (parsed.temps);
}
