/*
 * ntc_stub.cpp -- Stub temperature reading for native tests
 *
 * Returns fixed temperatures for testing protocol logic without hardware.
 */

#include "ntc.h"

/* Fixed test temperatures (tenths of degrees) */
static int16_t stub_temps[TMON_NUM_CHANNELS] = {235, 198, TMON_TEMP_INVALID, TMON_TEMP_INVALID};

void
tmon_ntc_init (void)
{
  /* Nothing to initialize in stub */
}

void
tmon_ntc_read_temps (int16_t temps[TMON_NUM_CHANNELS])
{
  int i;
  for (i = 0; i < TMON_NUM_CHANNELS; i++)
    {
      temps[i] = stub_temps[i];
    }
}

/*
 * Test helper: set stub temperatures.
 * Not declared in header -- only for test code.
 */
void
tmon_ntc_stub_set (int16_t t0, int16_t t1, int16_t t2, int16_t t3)
{
  stub_temps[0] = t0;
  stub_temps[1] = t1;
  stub_temps[2] = t2;
  stub_temps[3] = t3;
}
