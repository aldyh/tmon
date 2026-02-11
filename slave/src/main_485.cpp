/*
 * tmon slave firmware -- UART protocol handler
 *
 * Listens for POLL requests on UART and responds with temperature readings.
 * Boot button (GPIO 0) blinks yellow N times (N = config_slave_addr).
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

#include "config.h"
#include "handler.h"
#include "led.h"
#include "log.h"
#include "protocol.h"
#include "sensors.h"

/* Pin assignments per docs/wiring.org */
static const int PIN_UART_RX = 16;
static const int PIN_UART_TX = 17;
static const int PIN_DE_RE   = 5;

/* Boot button (active LOW, internal pull-up) */
static const int PIN_BUTTON = 0;
static const unsigned long BUTTON_DEBOUNCE_MS = 500;

/* RS-485 bus parameters per docs/protocol.org */
static const int UART_BAUD = 9600;

/* Receive buffer */
static const size_t RX_BUF_SIZE = 64;
static uint8_t rx_buf[RX_BUF_SIZE];
static size_t rx_len = 0;

/* Transmit buffer */
static const size_t TX_BUF_SIZE = 64;
static uint8_t tx_buf[TX_BUF_SIZE];

/* Inter-byte timeout (ms) for frame assembly */
static const unsigned long FRAME_TIMEOUT_MS = 50;
static unsigned long last_rx_time = 0;

/* Button state */
static unsigned long last_button_ms = 0;

void
setup (void)
{
  /* USB serial for debug output */
  Serial.begin (115200);
  delay (5000);  /* Wait for USB CDC to enumerate */

  config_init ();

  Serial.println ("tmon slave starting");
  Serial.print ("Address: ");
  Serial.println (config_slave_addr);

  tmon_sensors_init ();
  led_init ();
  pinMode (PIN_BUTTON, INPUT_PULLUP);

  /* DE/RE pin: LOW = receive, HIGH = transmit */
  pinMode (PIN_DE_RE, OUTPUT);
  digitalWrite (PIN_DE_RE, LOW);

  /* UART for RS-485 communication */
  Serial1.begin (UART_BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
  Serial.println ("UART configured, waiting for POLL...");
}

void
loop (void)
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

  /* Check for inter-byte timeout (frame boundary) */
  if (rx_len > 0 && (now - last_rx_time) > FRAME_TIMEOUT_MS)
    {
      Serial.print ("RX frame: ");
      Serial.print (rx_len);
      Serial.println (" bytes");

      /* Try to process the accumulated bytes */
      size_t tx_len = tmon_handler_process (config_slave_addr, rx_buf, rx_len,
                                            tx_buf, TX_BUF_SIZE);
      if (tx_len > 0)
        {
          /* Send response */
          digitalWrite (PIN_DE_RE, HIGH);  /* transmit mode */
          Serial1.write (tx_buf, tx_len);
          Serial1.flush ();                /* wait for TX complete */
          digitalWrite (PIN_DE_RE, LOW);   /* back to receive mode */

          /* Log temps from the actual response payload */
          struct tmon_reply_payload parsed;
          tmon_parse_reply (&tx_buf[4], TMON_REPLY_PAYLOAD_LEN, &parsed);
          Serial.print ("TX REPLY: ");
          Serial.print (tx_len);
          Serial.print (" bytes, ");
          log_temps (parsed.temps);
        }
      else
        {
          Serial.println ("No response generated");
        }

      /* Reset receive buffer */
      rx_len = 0;
    }

  /* Read incoming bytes */
  while (Serial1.available () && rx_len < RX_BUF_SIZE)
    {
      rx_buf[rx_len++] = Serial1.read ();
      last_rx_time = now;
    }
}
