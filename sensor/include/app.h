/*
 * app.h -- Sensor application base class
 *
 * Shared setup/loop skeleton for tmon sensor firmware.
 * Transport-specific subclasses override transport_init and
 * transport_loop to implement RS-485 or UDP communication.
 */

#ifndef TMON_APP_H
#define TMON_APP_H

#include <stddef.h>
#include <stdint.h>

class SensorApp
{
  unsigned long last_button_ms;

  virtual void transport_init () = 0;
  virtual void transport_loop () = 0;

protected:
  static const size_t BUF_SIZE = 64;
  uint8_t tx_buf[BUF_SIZE];

  void check_button ();
  void log_reply (const char *label, size_t len);

public:
  void setup ();
  void loop ();
};

#endif /* TMON_APP_H */
