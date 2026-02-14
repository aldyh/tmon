/*
 * app.cpp -- Sensor application base class
 *
 * Shared setup/loop skeleton and helpers used by all transports.
 */

#include "app.h"

#include <Arduino.h>

#include "config.h"
#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* Boot button (active LOW, internal pull-up) */
static const int BOOT_BUTTON = 0;

/*
 * SensorApp::setup -- Common hardware init, then transport-specific init.
 *
 * Initializes serial debug output, configuration, temperature sensors,
 * status LED, and boot button.  Subclasses add transport setup in
 * transport_init().
 */
void
SensorApp::setup ()
{
  Serial.begin (115200);
  delay (5000);

  config_init ();
  tmon_sensors_init ();
  led_init ();
  pinMode (BOOT_BUTTON, INPUT_PULLUP);

  transport_init ();
}

/*
 * SensorApp::loop -- Check boot button, then run transport loop.
 */
void
SensorApp::loop ()
{
  check_button ();
  transport_loop ();
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
      && (now - last_button_ms) >= 500)
    {
      last_button_ms = now;
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
  struct tmon_reply_payload parsed;
  tmon_parse_reply (&tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
  Serial.print (label);
  Serial.print (len);
  Serial.print (" bytes, ");
  log_temps (parsed.temps);
}
