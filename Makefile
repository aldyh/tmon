.PHONY: all build-master build-slave-485 build-slave-udp \
       flash-slave-485 flash-slave-udp \
       run-master-485 run-master-udp \
       demo-setup \
       check check-master check-slave check-integration check-demo \
       demo-generate demo-server \
       demo-static demo-static-tar demo-static-upload demo-static-clean \
       firmware \
       install uninstall clean

MASTER_STAMP := master/.venv/.installed
PANEL_STAMP  := panel/.venv/.installed

all: build-master

build-master: $(MASTER_STAMP)

master/.venv:
	python3 -m venv master/.venv

$(MASTER_STAMP): master/.venv master/pyproject.toml
	. master/.venv/bin/activate && pip install -e "master/.[test]"
	touch $(MASTER_STAMP)

build-slave-485:
	cd slave && pio run -e uart

build-slave-udp:
	cd slave && pio run -e udp

flash-slave-485: build-slave-485
ifndef SLAVE_ADDR
	$(error SLAVE_ADDR required, e.g. make flash-slave-485 SLAVE_ADDR=1)
endif
	deploy/tmon-flash --mode=serial --addr=$(SLAVE_ADDR)

flash-slave-udp: build-slave-udp
ifndef SLAVE_ADDR
	$(error SLAVE_ADDR required, e.g. make flash-slave-udp SLAVE_ADDR=1)
endif
	deploy/tmon-flash --mode=udp --addr=$(SLAVE_ADDR)

run-master-485: $(MASTER_STAMP)
	cd master && . .venv/bin/activate && tmon config-485.toml

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
	if command -v pio >/dev/null 2>&1; then cd slave && pio test -e native; \
	else echo "pio not found, skipping slave tests"; fi

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
# Build generic firmware binaries (one per transport mode) and collect
# in firmware/.  Config is patched into the binary at flash time by
# tmon-patch, so no per-address builds are needed.

BOOT_APP0 := $(shell find ~/.platformio/packages/framework-arduinoespressif32 \
               -name boot_app0.bin 2>/dev/null | head -1)

firmware: build-slave-485 build-slave-udp
	mkdir -p firmware
	cp slave/.pio/build/uart/firmware.bin firmware/firmware-serial.bin
	cp slave/.pio/build/udp/firmware.bin firmware/firmware-udp.bin
	cp slave/.pio/build/uart/bootloader.bin firmware/bootloader.bin
	cp slave/.pio/build/uart/partitions.bin firmware/partitions.bin
ifdef BOOT_APP0
	cp $(BOOT_APP0) firmware/boot_app0.bin
else
	@echo "warning: boot_app0.bin not found in PlatformIO packages"
endif
	@echo "Firmware collected in firmware/"
	@ls -1 firmware/

install:
	deploy/install.sh

uninstall:
	deploy/uninstall.sh

clean: demo-static-clean
	rm -rf firmware master/.venv panel/.venv panel/tmon_mock.db
	if command -v pio >/dev/null 2>&1; then cd slave && pio run -t clean; fi
