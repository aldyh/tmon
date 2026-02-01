"""Poll loop for querying slave devices.

Periodically sends poll requests to each configured slave and
collects temperature readings.

Example:
    >>> from tmon.poller import Poller
    >>> poller = Poller(bus=bus, storage=storage, slaves=[1, 2])
    >>> poller.run_once()
"""


class Poller:
    """Polls slave devices on a schedule.

    Args:
        bus: A Bus instance for serial communication.
        storage: A Storage instance for persisting readings.
        slaves: List of slave addresses to poll.
    """

    def __init__(self, bus, storage, slaves):
        """Initialize the poller.

        Args:
            bus: Bus instance for sending/receiving frames.
            storage: Storage instance for writing readings.
            slaves: List of integer slave addresses.
        """
        raise NotImplementedError

    def run_once(self):
        """Execute a single poll cycle across all slaves.

        Returns:
            list: Collected readings from this cycle.
        """
        raise NotImplementedError
