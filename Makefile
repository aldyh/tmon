.PHONY: all build-master build-slave check check-master check-slave check-simulator clean

MASTER_STAMP := master/.venv/.installed

all: build-master build-slave

build-master: $(MASTER_STAMP)

master/.venv:
	python3 -m venv master/.venv

$(MASTER_STAMP): master/.venv master/pyproject.toml
	. master/.venv/bin/activate && pip install -e "master/.[test]"
	touch $(MASTER_STAMP)

build-slave:
	cd slave && pio run

check: check-master check-slave check-simulator

check-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m "not integration"

check-slave:
	cd slave && pio test -e native

check-simulator: $(MASTER_STAMP)
	@export TMPDIR=$$(mktemp -d); \
	socat -d -d \
		"PTY,raw,echo=0,link=$$TMPDIR/master" \
		"PTY,raw,echo=0,link=$$TMPDIR/slave" & \
	SOCAT_PID=$$!; \
	for i in $$(seq 1 20); do \
		[ -e "$$TMPDIR/master" ] && [ -e "$$TMPDIR/slave" ] && break; \
		sleep 0.1; \
	done; \
	. master/.venv/bin/activate && \
	python3 master/tools/simulator.py "$$TMPDIR/slave" 1 & \
	SIM_PID=$$!; \
	sleep 0.5; \
	python3 master/tools/check_simulator.py "$$TMPDIR/master" 1; \
	RC=$$?; \
	kill $$SIM_PID 2>/dev/null || true; \
	kill $$SOCAT_PID 2>/dev/null || true; \
	rm -rf "$$TMPDIR"; \
	exit $$RC

clean:
	rm -rf master/.venv
	cd slave && pio run -t clean
