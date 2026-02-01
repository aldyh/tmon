# Wiring Reference

This document describes how to wire each ESP32 slave node
(ESP32-WROOM-32 module) to an RS-485 bus with up to four NTC
thermistors.

## Pin assignments

| Function       | ESP32 GPIO | Notes                          |
|----------------|------------|--------------------------------|
| UART2 TX       | GPIO 17    | To MAX485 DI                   |
| UART2 RX       | GPIO 16    | From MAX485 RO                 |
| RS-485 DE/RE   | GPIO 4     | To MAX485 DE and RE (tied)     |
| NTC channel 0  | GPIO 32    | ADC1_CH4                       |
| NTC channel 1  | GPIO 33    | ADC1_CH5                       |
| NTC channel 2  | GPIO 34    | ADC1_CH6 (input-only pin)      |
| NTC channel 3  | GPIO 35    | ADC1_CH7 (input-only pin)      |

**Why ADC1?**  ADC2 cannot be used while WiFi is active.  All
thermistor inputs are on ADC1 so WiFi remains available if needed.

**Why UART2?**  UART0 (GPIO 1/3) is reserved for USB
programming/debug.  UART1 default pins (GPIO 9/10) conflict with the
internal flash.  UART2 on GPIO 16/17 is free on WROOM-32 modules
without PSRAM.

## MAX485 wiring

The MAX485 is a half-duplex RS-485 transceiver.  DE (Driver Enable)
and RE (Receiver Enable, active low) are tied together so a single
GPIO controls bus direction.

```
ESP32                MAX485               RS-485 bus
-----                ------               ----------
GPIO 17 (TX) ------> DI
GPIO 16 (RX) <------ RO
GPIO  4      ------> DE
             ------> RE (active low)
                      A  ------------->  A
                      B  ------------->  B
             GND ---- GND ------------>  GND
             3.3V --- VCC
```

**Bus direction logic:**

- **Transmit:** drive DE/RE pin HIGH.  DE is asserted, RE is
  deasserted, the driver is enabled.
- **Receive:** drive DE/RE pin LOW.  DE is deasserted, RE is
  asserted (active low), the receiver is enabled.
- The firmware must switch to receive immediately after the last
  byte is transmitted.

## NTC thermistor voltage divider

Each NTC thermistor is read through a voltage divider against a
fixed 10k-ohm reference resistor.

```
3.3V
 |
[10k fixed resistor]
 |
 +-------> GPIO 32/33/34/35 (ADC input)
 |
[NTC thermistor]
 |
GND
```

With this arrangement (fixed resistor on the high side, NTC on the
low side), the ADC voltage decreases as temperature rises (NTC
resistance drops).

**Component values:**

- NTC thermistor: 10k ohm at 25 C (standard B=3950 type).
- Reference resistor: 10k ohm, 1% tolerance.

**Optional:** a 100 nF ceramic capacitor from the ADC input to GND
can reduce noise on the reading.

## RS-485 bus wiring

All nodes (master USB adapter + ESP32 slaves) share a single
twisted pair plus ground.

```
Pi (USB-RS485)       Slave 1         Slave 2         Slave N
   A ----+-----------+- A --+---------+- A --+-- ... --+- A
   B ----+-----------+- B --+---------+- B --+-- ... --+- B
  GND ---+-----------+- GND-+---------+- GND-+-- ... --+- GND
         |                                              |
      [120R]                                         [120R]
      (term.)                                        (term.)
```

- Use twisted pair cable for A/B.  Run a separate ground wire.
- 120-ohm termination resistors at both physical ends of the bus.
- Keep the bus under 30 meters for a home installation; this is
  well within RS-485 limits.
- At 9600 baud there is generous margin for cable length and noise.

## Raspberry Pi side

The master uses a USB-to-RS-485 adapter (e.g., a cheap CH340 or
FTDI-based dongle).  No additional wiring is needed on the Pi
beyond plugging in the adapter and connecting A, B, GND to the bus.

The adapter typically appears as `/dev/ttyUSB0`.

## Power

- Each ESP32 node is independently powered (USB or a local 3.3V/5V
  supply).
- The MAX485 VCC is connected to the ESP32 3.3V rail.
- All nodes must share a common ground via the bus GND wire.
