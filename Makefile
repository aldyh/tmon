.PHONY: check check-master check-slave

check: check-master check-slave

check-master:
	cd master && . .venv/bin/activate && pytest

check-slave:
	cd slave && pio test -e native
