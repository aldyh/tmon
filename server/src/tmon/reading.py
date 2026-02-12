"""Transport-neutral temperature reading dataclass.

Used by both the RS-485 poller and UDP listener to represent
a single set of temperature readings from a sensor device.

Example:
    >>> from tmon.reading import Reading
    >>> r = Reading(addr=3, temp_0=235, temp_1=198, temp_2=None, temp_3=None)
    >>> r.addr
    3
"""

from dataclasses import dataclass


@dataclass
class Reading:
    """A single temperature reading from a sensor device.

    Temperatures are in tenths of a degree C, or None if invalid.
    """

    addr: int
    temp_0: int | None
    temp_1: int | None
    temp_2: int | None
    temp_3: int | None


def fmt_temp(t: int | None) -> str:
    """Format a raw int16 temperature for display.

    Example:
        >>> fmt_temp(235)
        '23.5'
        >>> fmt_temp(None)
        '--.-'
    """
    return f"{t / 10:.1f}" if t is not None else "--.-"
