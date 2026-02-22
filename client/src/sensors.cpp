/*
 * sensors.cpp -- NTC thermistor temperature reading (ESP32)
 *
 * Reads 4 NTC thermistors on ADC1 channels (GPIO 1-4 on ESP32-S3).
 * Uses B parameter equation for temperature conversion.
 *
 * Hardware setup (per docs/wiring.org):
 *   3.3V -> 10k fixed resistor -> ADC input -> NTC 10k -> GND
 *   Voltage drops as temperature rises (NTC resistance decreases).
 */

#include "sensors.h"
#include <Arduino.h>
#include <math.h>

/* ADC pins for temperature channels 0-3 (ESP32-S3 ADC1) */
static const int ADC_PINS[TMON_NUM_CHANNELS] = {1, 2, 3, 4};

/* NTC parameters for 10k thermistor */
static const float NTC_NOMINAL_R = 10000.0f;  /* 10k at 25C */
static const float NTC_NOMINAL_T = 298.15f;   /* 25C in Kelvin */
static const float NTC_BETA = 3950.0f;        /* B coefficient */
static const float SERIES_R = 10000.0f;       /* 10k series resistor */

/* ADC parameters */
static const int ADC_MAX = 4095;              /* 12-bit ADC */
static const float VCC = 3.3f;

/* Thresholds for detecting unconnected NTC */
static const int ADC_MIN_VALID = 100;         /* Below this = shorted */
static const int ADC_MAX_VALID = 3995;        /* Above this = open */

/*
 * tmon_sensor_init -- Initialize ADC for temperature reading.
 *
 * Call once at startup before tmon_sensor_read_temps().
 */
void
tmon_sensor_init (void)
{
  int i;
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      pinMode (ADC_PINS[i], INPUT);
    }
  /* ESP32 ADC defaults to 12-bit, no additional setup needed */
}

/*
 * Convert ADC reading to temperature using B parameter equation.
 *
 * Voltage divider: V_adc = V_cc * R_ntc / (R_series + R_ntc)
 * Solve for R_ntc: R_ntc = R_series * V_adc / (V_cc - V_adc)
 *
 * B parameter equation:
 *   1/T = 1/T0 + (1/B) * ln(R/R0)
 *   T = 1 / (1/T0 + ln(R/R0)/B)
 */
static int16_t
adc_to_temp (int adc_value)
{
  float voltage, r_ntc, inv_temp, temp_c;

  /* Convert ADC to voltage */
  voltage = (adc_value * VCC) / ADC_MAX;

  /* Solve for NTC resistance */
  if (voltage >= VCC - 0.01f)
    return TMON_TEMP_INVALID;  /* Would divide by zero */

  r_ntc = SERIES_R * voltage / (VCC - voltage);

  /* B parameter equation */
  inv_temp = logf (r_ntc / NTC_NOMINAL_R) / NTC_BETA;
  inv_temp += 1.0f / NTC_NOMINAL_T;
  temp_c = (1.0f / inv_temp) - 273.15f;

  /* Convert to tenths of degree and clamp to valid range */
  int temp_tenths = (int)(temp_c * 10.0f + 0.5f);
  if (temp_tenths < -32768)
    temp_tenths = -32768;
  if (temp_tenths > 32766)  /* Reserve 32767 for invalid */
    temp_tenths = 32766;

  return (int16_t)temp_tenths;
}

/*
 * tmon_sensor_read_temps -- Read temperatures from all 4 channels.
 *
 * Reads ADC values, converts to temperature using B parameter equation.
 * Unconnected channels (ADC reads 0 or near-max) report TMON_TEMP_INVALID.
 *
 * Args:
 *   temps: Output array of 4 int16_t values (tenths of degree C).
 */
void
tmon_sensor_read_temps (int16_t temps[TMON_NUM_CHANNELS])
{
  int i;
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      int adc = analogRead (ADC_PINS[i]);

      /* Detect unconnected channel */
      if (adc < ADC_MIN_VALID || adc > ADC_MAX_VALID)
        {
          temps[i] = TMON_TEMP_INVALID;
        }
      else
        {
          temps[i] = adc_to_temp (adc);
        }
    }
}
