/*
 * tmon sensor firmware -- RS-485 transport
 *
 * Listens for POLL requests on UART and responds with temperature readings.
 * Blinks green after each send.
 * Boot button (GPIO 0) blinks yellow N times (N = config_sensor_addr).
 * Protocol defined in docs/protocol.org.
 *
 * Wiring (with MAX485):
 *   ESP32 GPIO 17 (TX) -> MAX485 DI
 *   ESP32 GPIO 16 (RX) <- MAX485 RO
 *   ESP32 GPIO 5 -> MAX485 DE + RE
 *
 * Debug output on USB serial (115200 baud).
 */

#include <Arduino.h>

#include "app.h"
#include "config.h"
#include "handler.h"
#include "led.h"

/* Pin assignments per docs/wiring.org */
static const int PIN_UART_RX = 16;
static const int PIN_UART_TX = 17;
static const int PIN_DE_RE   = 5;

/* RS-485 bus parameters per docs/protocol.org */
static const int UART_BAUD = 9600;

class RS485Sensor : public SensorApp
{
  static const size_t RX_BUF_SIZE = 64;
  uint8_t rx_buf[RX_BUF_SIZE];
  size_t rx_len = 0;
  unsigned long last_rx_time = 0;

  void on_init () override;
  void on_loop () override;
};

void
RS485Sensor::on_init ()
{
  Serial.println ("tmon sensor starting");
  Serial.print ("Address: ");
  Serial.println (config_sensor_addr);

  /* DE/RE pin: LOW = receive, HIGH = transmit */
  pinMode (PIN_DE_RE, OUTPUT);
  digitalWrite (PIN_DE_RE, LOW);

  /* UART for RS-485 communication */
  Serial1.begin (UART_BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
  Serial.println ("UART configured, waiting for POLL...");
}

void
RS485Sensor::on_loop ()
{
  unsigned long now = millis ();

  /* Read incoming bytes */
  while (Serial1.available () && rx_len < RX_BUF_SIZE)
    {
      rx_buf[rx_len++] = Serial1.read ();
      last_rx_time = now;
    }

  /* Check for inter-byte timeout (frame boundary) */
  if (rx_len > 0 && (now - last_rx_time) > 50)
    {
      Serial.print ("RX frame: ");
      Serial.print (rx_len);
      Serial.println (" bytes");

      /* Try to process the accumulated bytes */
      size_t tx_len = tmon_handler_process (config_sensor_addr, rx_buf, rx_len,
                                            tx_buf, BUF_SIZE);
      if (tx_len > 0)
        {
          /* Send response */
          digitalWrite (PIN_DE_RE, HIGH);  /* transmit mode */
          Serial1.write (tx_buf, tx_len);
          Serial1.flush ();                /* wait for TX complete */
          digitalWrite (PIN_DE_RE, LOW);   /* back to receive mode */
          led_tx_blink ();
          log_reply ("TX REPLY: ", tx_len);
        }
      else
        {
          Serial.println ("No response generated");
        }

      /* Reset receive buffer */
      rx_len = 0;
    }
}

static RS485Sensor sensor;

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
