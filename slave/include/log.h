/*
 * log.h -- Debug logging helpers for tmon slave
 *
 * Inline functions for logging to Arduino Serial.
 */

#ifndef TMON_LOG_H
#define TMON_LOG_H

#include <Arduino.h>
#include "protocol.h"

/*
 * log_temps -- Log temperature readings to serial.
 *
 * Prints temps in human-readable format: temps=[23.4, 25.1, --.-, 22.0]
 */
static inline void
log_temps (const int16_t *temps)
{
  Serial.print ("temps=[");
  for (int i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      if (i > 0)
        Serial.print (", ");
      if (temps[i] == TMON_TEMP_INVALID)
        Serial.print ("--.-");
      else
        {
          Serial.print (temps[i] / 10);
          Serial.print (".");
          Serial.print (abs (temps[i]) % 10);
        }
    }
  Serial.println ("]");
}

#endif /* TMON_LOG_H */
