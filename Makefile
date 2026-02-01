.PHONY: all build-master build-slave check check-master check-slave

all: build-master build-slave

build-master:
	cd master && python3 -m venv .venv \
	  && . .venv/bin/activate \
	  && pip install -e ".[test]"

build-slave:
	cd slave && pio run

check: check-master check-slave

check-master:
	cd master && . .venv/bin/activate && pytest

check-slave:
	cd slave && pio test -e native
