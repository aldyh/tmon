.PHONY: all build-master build-slave build-panel \
       check check-master check-slave check-integration check-panel \
       generate-panel-data run-panel mock-panel \
       demo demo-tar demo-upload demo-clean clean

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

mock-panel: generate-panel-data
	@echo "Starting panel at http://localhost:5000"
	$(MAKE) run-panel

demo: generate-panel-data
	cd panel && . .venv/bin/activate && python build_demo.py --db tmon_mock.db --output demo

demo-tar: demo
	tar czf tmon-demo.tar.gz --transform='s,^panel/demo,tmon-demo,' panel/demo

demo-upload: demo-tar
	scp tmon-demo.tar.gz quesejoda.com:
	ssh quesejoda.com 'rm -rf ~/quesejoda.com/tmon-demo/ && cd ~/quesejoda.com && tar xzf ~/tmon-demo.tar.gz && chmod -R a+rX ~/quesejoda.com/tmon-demo/'

demo-clean:
	rm -rf panel/demo tmon-demo.tar.gz

clean: demo-clean
	rm -rf master/.venv panel/.venv panel/tmon_mock.db
	cd slave && pio run -t clean
