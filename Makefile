.PHONY: all build-master build-slave check check-master check-slave clean

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

check: check-master check-slave

check-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest

check-slave:
	cd slave && pio test -e native

clean:
	rm -rf master/.venv
	cd slave && pio run -t clean
