/*
 * sensors.h -- NTC thermistor temperature reading
 *
 * Reads 4 temperature channels from NTC thermistors connected to ADC.
 * Uses B parameter equation for temperature conversion.
 */

#ifndef TMON_SENSORS_H
#define TMON_SENSORS_H

#include <stdint.h>
#include "protocol.h"

void tmon_sensor_init (void);
void tmon_sensor_read_temps (int16_t temps[TMON_NUM_CHANNELS]);

#endif /* TMON_SENSORS_H */
