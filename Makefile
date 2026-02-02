.PHONY: all build-master build-slave demo-setup \
       check check-master check-slave check-integration check-demo \
       demo-generate demo-server \
       demo-static demo-static-tar demo-static-upload demo-static-clean clean

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

demo-setup: $(PANEL_STAMP)

panel/.venv:
	python3 -m venv panel/.venv

$(PANEL_STAMP): panel/.venv panel/pyproject.toml
	. panel/.venv/bin/activate && pip install -e "panel/.[test]"
	touch $(PANEL_STAMP)

check: check-master check-slave check-integration check-demo

check-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m "not integration"

check-slave:
	cd slave && pio test -e native

check-integration: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && pytest -m integration -v

check-demo: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && pytest

demo-generate: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && python generate_data.py

demo-server: demo-generate
	@echo "Starting panel at http://localhost:5000"
	cd panel && . .venv/bin/activate && flask --app app run

demo-static: demo-generate
	cd panel && . .venv/bin/activate && python build_demo.py --db tmon_mock.db --output demo

demo-static-tar: demo-static
	tar czf tmon-demo.tar.gz --transform='s,^panel/demo,tmon-demo,' panel/demo

demo-static-upload: demo-static-tar
	scp tmon-demo.tar.gz quesejoda.com:
	ssh quesejoda.com 'rm -rf ~/quesejoda.com/tmon-demo/ && cd ~/quesejoda.com && tar xzf ~/tmon-demo.tar.gz && chmod -R a+rX ~/quesejoda.com/tmon-demo/'

demo-static-clean:
	rm -rf panel/demo tmon-demo.tar.gz

clean: demo-static-clean
	rm -rf master/.venv panel/.venv panel/tmon_mock.db
	cd slave && pio run -t clean
