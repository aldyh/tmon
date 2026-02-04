/*
 * sensors.h -- NTC thermistor temperature reading
 *
 * Reads 4 temperature channels from NTC thermistors connected to ADC.
 * Uses Steinhart-Hart equation for temperature conversion.
 */

#ifndef TMON_SENSORS_H
#define TMON_SENSORS_H

#include <stdint.h>
#include "protocol.h"

#ifdef __cplusplus
extern "C" {
#endif

void tmon_sensors_init (void);
void tmon_read_temps (int16_t temps[TMON_NUM_CHANNELS]);

#ifdef __cplusplus
}
#endif

#endif /* TMON_SENSORS_H */
