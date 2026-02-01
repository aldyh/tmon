"""Configuration loading from TOML files.

Reads config.toml using Python 3.11+ stdlib tomllib.

Example:
    >>> from tmon.config import load_config
    >>> cfg = load_config(path="config.toml")
    >>> print(cfg["serial"]["port"])
"""


def load_config(path):
    """Load and return configuration from a TOML file.

    Args:
        path: Filesystem path to the TOML configuration file.

    Returns:
        dict: Parsed configuration dictionary.
    """
    raise NotImplementedError
