.PHONY: all build-master build-slave build-slave-udp \
       flash-slave flash-slave-udp \
       run-master run-master-udp \
       demo-setup \
       check check-master check-slave check-integration check-demo \
       demo-generate demo-server \
       demo-static demo-static-tar demo-static-upload demo-static-clean \
       firmware firmware-clean \
       install uninstall clean

MASTER_STAMP := master/.venv/.installed
PANEL_STAMP  := panel/.venv/.installed

all: build-master build-slave build-slave-udp

build-master: $(MASTER_STAMP)

master/.venv:
	python3 -m venv master/.venv

$(MASTER_STAMP): master/.venv master/pyproject.toml
	. master/.venv/bin/activate && pip install -e "master/.[test]"
	touch $(MASTER_STAMP)

build-slave:
	cd slave && pio run -e uart

build-slave-udp:
	cd slave && pio run -e udp

flash-slave:
ifndef SLAVE_ADDR
	$(error SLAVE_ADDR required, e.g. make flash-slave SLAVE_ADDR=1)
endif
	cd slave && SLAVE_ADDR=$(SLAVE_ADDR) pio run -e uart -t upload

flash-slave-udp:
ifndef SLAVE_ADDR
	$(error SLAVE_ADDR required, e.g. make flash-slave-udp SLAVE_ADDR=1)
endif
	cd slave && SLAVE_ADDR=$(SLAVE_ADDR) pio run -e udp -t upload

run-master: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && tmon config.toml

run-master-udp: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && tmon config-udp.toml

demo-setup: $(PANEL_STAMP)

panel/.venv:
	python3 -m venv panel/.venv

$(PANEL_STAMP): panel/.venv panel/pyproject.toml master/pyproject.toml
	. panel/.venv/bin/activate && pip install -e master -e "panel/.[test]"
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
	cd panel && . .venv/bin/activate && TMON_DB=tmon_mock.db flask --app app run

demo-static: demo-generate
	cd panel && . .venv/bin/activate && python build_demo.py --db tmon_mock.db --output demo

demo-static-tar: demo-static
	tar czf tmon-demo.tar.gz --transform='s,^panel/demo,tmon-demo,' panel/demo

demo-static-upload: demo-static-tar
	scp tmon-demo.tar.gz quesejoda.com:
	ssh quesejoda.com 'rm -rf ~/quesejoda.com/tmon-demo/ && cd ~/quesejoda.com && tar xzf ~/tmon-demo.tar.gz && chmod -R a+rX ~/quesejoda.com/tmon-demo/'

demo-static-clean:
	rm -rf panel/demo tmon-demo.tar.gz

# ---- Firmware collection ----
# Build all firmware variants and collect in firmware/.

SERIAL_SLAVES ?= 1 2 3 4
UDP_SLAVES    ?= 5 6 7 8

BOOT_APP0 := $(shell find ~/.platformio/packages/framework-arduinoespressif32 \
               -name boot_app0.bin 2>/dev/null | head -1)

firmware:
	mkdir -p firmware
	@for addr in $(SERIAL_SLAVES); do \
	  echo "Building serial firmware for addr $$addr..."; \
	  cd slave && SLAVE_ADDR=$$addr pio run -e uart && cd ..; \
	  cp slave/.pio/build/uart/firmware.bin firmware/firmware-serial-$$addr.bin; \
	done
	@for addr in $(UDP_SLAVES); do \
	  echo "Building UDP firmware for addr $$addr..."; \
	  cd slave && SLAVE_ADDR=$$addr pio run -e udp && cd ..; \
	  cp slave/.pio/build/udp/firmware.bin firmware/firmware-udp-$$addr.bin; \
	done
	cp slave/.pio/build/uart/bootloader.bin firmware/bootloader.bin
	cp slave/.pio/build/uart/partitions.bin firmware/partitions.bin
ifdef BOOT_APP0
	cp $(BOOT_APP0) firmware/boot_app0.bin
else
	@echo "warning: boot_app0.bin not found in PlatformIO packages"
endif
	@echo "Firmware collected in firmware/"
	@ls -1 firmware/

firmware-clean:
	rm -rf firmware

install:
	sudo deploy/install.sh

uninstall:
	sudo deploy/uninstall.sh

clean: demo-static-clean firmware-clean
	rm -rf master/.venv panel/.venv panel/tmon_mock.db
	cd slave && pio run -t clean
