/*
 * app.h -- Client application base class
 *
 * Shared setup/loop skeleton for tmon client firmware.
 * Subclasses override on_init and on_loop to implement their
 * communication strategy (poll-response, push, etc.).
 */

#ifndef TMON_APP_H
#define TMON_APP_H

#include <stddef.h>
#include <stdint.h>

class ClientApp
{
  static const size_t BUF_SIZE = 64;
  unsigned long m_last_button_ms;

  virtual void on_init () = 0;
  virtual void on_loop () = 0;

protected:
  uint8_t m_tx_buf[BUF_SIZE];

  size_t build_reply_frame (uint8_t addr);
  size_t dispatch_frame (uint8_t addr, const uint8_t *data, size_t len);

  void check_button ();
  void log_temps (const char *label, size_t len);

public:
  void setup ();
  void loop ();
};

#endif /* TMON_APP_H */
