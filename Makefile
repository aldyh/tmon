.PHONY: all build-server build-sensor-485 build-sensor-udp \
       flash-sensor-485 flash-sensor-udp \
       run-server-485 run-server-udp \
       demo-setup \
       check check-server check-sensor check-integration check-demo \
       demo-generate demo-server \
       demo-static demo-static-tar demo-static-upload demo-static-clean \
       firmware \
       install uninstall clean

SERVER_STAMP := server/.venv/.installed
PANEL_STAMP  := panel/.venv/.installed

all: build-server

build-server: $(SERVER_STAMP)

server/.venv:
	python3 -m venv server/.venv

$(SERVER_STAMP): server/.venv server/pyproject.toml
	. server/.venv/bin/activate && pip install -e "server/.[test]"
	touch $(SERVER_STAMP)

build-sensor-485:
	cd sensor && pio run -e uart

build-sensor-udp:
	cd sensor && pio run -e udp

flash-sensor-485: build-sensor-485
ifndef SENSOR_ADDR
	$(error SENSOR_ADDR required, e.g. make flash-sensor-485 SENSOR_ADDR=1)
endif
	deploy/tmon-flash --mode=serial --addr=$(SENSOR_ADDR)

flash-sensor-udp: build-sensor-udp
ifndef SENSOR_ADDR
	$(error SENSOR_ADDR required, e.g. make flash-sensor-udp SENSOR_ADDR=1)
endif
	deploy/tmon-flash --mode=udp --addr=$(SENSOR_ADDR)

run-server-485: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && tmon config-485.toml

run-server-udp: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && tmon config-udp.toml

demo-setup: $(PANEL_STAMP)

panel/.venv:
	python3 -m venv panel/.venv

$(PANEL_STAMP): panel/.venv panel/pyproject.toml server/pyproject.toml
	. panel/.venv/bin/activate && pip install -e server -e "panel/.[test]"
	touch $(PANEL_STAMP)

check: check-server check-sensor check-integration check-demo

check-server: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && pytest -m "not integration"

check-sensor:
	if command -v pio >/dev/null 2>&1; then cd sensor && pio test -e native; \
	else echo "pio not found, skipping sensor tests"; fi

check-integration: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && pytest -m integration -v

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

firmware: build-sensor-485 build-sensor-udp
	mkdir -p firmware
	cp sensor/.pio/build/uart/firmware.bin firmware/firmware-serial.bin
	cp sensor/.pio/build/udp/firmware.bin firmware/firmware-udp.bin
	cp sensor/.pio/build/uart/bootloader.bin firmware/bootloader.bin
	cp sensor/.pio/build/uart/partitions.bin firmware/partitions.bin
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
	rm -rf firmware server/.venv panel/.venv panel/tmon_mock.db
	if command -v pio >/dev/null 2>&1; then cd sensor && pio run -t clean; fi
