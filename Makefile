.PHONY: all build-master build-slave build-panel \
       check check-master check-slave check-integration check-panel \
       generate-panel-data run-panel clean

MASTER_STAMP := master/.venv/.installed
PANEL_STAMP  := panel/.venv/.installed

all: build-master build-slave

build-master: $(MASTER_STAMP)

master/.venv:
	python3 -m venv master/.venv

$(MASTER_STAMP): master/.venv master/pyproject.toml
	. master/.venv/bin/activate && pip install -e "master/.[test]"
	touch $(MASTER_STAMP)

build-slave:
	cd slave && pio run

build-panel: $(PANEL_STAMP)

panel/.venv:
	python3 -m venv panel/.venv

$(PANEL_STAMP): panel/.venv panel/pyproject.toml
	. panel/.venv/bin/activate && pip install -e "panel/.[test]"
	touch $(PANEL_STAMP)

check: check-master check-slave check-integration check-panel

check-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m "not integration"

check-slave:
	cd slave && pio test -e native

check-integration: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m integration -v

check-panel: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && pytest

generate-panel-data: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && python generate_data.py

run-panel: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && flask --app app run

clean:
	rm -rf master/.venv panel/.venv panel/tmon_mock.db
	cd slave && pio run -t clean
