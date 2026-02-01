"""Project-wide configuration constants.

Central place for tuneable parameters shared across modules.
Import individual names where needed.

Example:
    >>> from tmon.config import BUS_TIMEOUT_MS
    >>> print(BUS_TIMEOUT_MS)
    200
"""

# Serial bus receive timeout in milliseconds.
BUS_TIMEOUT_MS = 200
