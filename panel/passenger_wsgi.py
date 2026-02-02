"""Passenger WSGI entry point for DreamHost (or any Passenger host).

Passenger looks for an ``application`` callable in this file.
The database path defaults to ``tmon_mock.db`` in the same directory.

Example (local test):
    $ TMON_DB=tmon_mock.db python -c "from passenger_wsgi import application; print(application)"
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# Passenger may use the system Python; point the venv packages in.
_VENV_PKGS = os.path.join(_HERE, ".venv", "lib")
if os.path.isdir(_VENV_PKGS):
    import glob
    for p in glob.glob(os.path.join(_VENV_PKGS, "python*", "site-packages")):
        if p not in sys.path:
            sys.path.insert(0, p)

os.environ.setdefault("TMON_DB", os.path.join(_HERE, "tmon_mock.db"))

from app import create_app  # noqa: E402

application = create_app(os.environ["TMON_DB"])
