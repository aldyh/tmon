/*
 * tmon slave firmware -- UART echo test
 *
 * Echoes bytes received on UART2 (GPIO 16 RX, GPIO 17 TX) back to sender.
 * Used to validate serial communication before adding protocol logic.
 *
 * Wiring (bare UART test, no MAX485):
 *   ESP32 GPIO 17 (TX) -> Pi GPIO 15 (RX)
 *   ESP32 GPIO 16 (RX) <- Pi GPIO 14 (TX)
 *   GND <-> GND
 *
 * Test from Pi:
 *   screen /dev/serial0 9600
 *   (type characters, they should echo back)
 *
 * Debug output on USB serial (115200 baud):
 *   screen /dev/ttyACM0 115200
 */

#include <Arduino.h>

/* Pin assignments per docs/wiring.org */
static const int PIN_UART_RX = 16;
static const int PIN_UART_TX = 17;
static const int PIN_DE_RE   = 5;

/* RS-485 bus runs at 9600 baud per docs/protocol.org */
static const int UART_BAUD = 9600;

void
setup (void)
{
  /* USB serial for debug output */
  Serial.begin (115200);
  Serial.println ("tmon echo test starting");

  /* DE/RE pin: LOW = receive, HIGH = transmit */
  pinMode (PIN_DE_RE, OUTPUT);
  digitalWrite (PIN_DE_RE, LOW);

  /* UART for RS-485 communication */
  Serial1.begin (UART_BAUD, SERIAL_8N1, PIN_UART_RX, PIN_UART_TX);
  Serial.println ("UART1 configured on GPIO 16 (RX) / GPIO 17 (TX)");
  Serial.println ("Waiting for data...");
}

void
loop (void)
{
  if (Serial1.available ())
    {
      /* Read incoming byte */
      int c = Serial1.read ();

      /* Debug: show what we received */
      Serial.print ("rx: 0x");
      Serial.print (c, HEX);
      if (c >= 0x20 && c < 0x7F)
        {
          Serial.print (" '");
          Serial.print ((char) c);
          Serial.print ("'");
        }
      Serial.println ();

      /* Echo it back */
      digitalWrite (PIN_DE_RE, HIGH);  /* transmit mode */
      Serial1.write (c);
      Serial1.flush ();                /* wait for TX complete */
      digitalWrite (PIN_DE_RE, LOW);   /* back to receive mode */
    }
}
