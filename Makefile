.PHONY: all build-master build-slave check check-master check-slave check-simulator check-integration clean

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

check: check-master check-slave check-simulator check-integration

check-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m "not integration"

check-slave:
	cd slave && pio test -e native

check-simulator: $(MASTER_STAMP)
	@master/tools/run_simulator.sh 1 & \
	SIM_SH_PID=$$!; \
	for i in $$(seq 1 40); do \
		[ -e /tmp/tmon-master ] && break; \
		sleep 0.1; \
	done; \
	sleep 0.3; \
	. master/.venv/bin/activate && \
	python3 master/tools/check_simulator.py /tmp/tmon-master 1; \
	RC=$$?; \
	kill $$SIM_SH_PID 2>/dev/null; \
	wait $$SIM_SH_PID 2>/dev/null || true; \
	exit $$RC

check-integration: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m integration -v

clean:
	rm -rf master/.venv
	cd slave && pio run -t clean
