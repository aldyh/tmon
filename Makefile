.PHONY: all server \
       run-server-485 run-server-udp \
       panel \
       check check-server check-firmware check-integration check-panel \
       generate-panel-mock-data run-panel \
       firmware firmware-485 firmware-udp \
       install uninstall purge clean \
       TAGS

SERVER_STAMP := server/.venv/.installed
PANEL_STAMP  := panel/.venv/.installed

all: server panel

server: $(SERVER_STAMP)

server/.venv:
	python3 -m venv server/.venv

$(SERVER_STAMP): server/.venv server/pyproject.toml
	. server/.venv/bin/activate && pip install -e "server/.[test]"
	touch $(SERVER_STAMP)

run-server-485: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && tmon tmon.toml --transport rs485

run-server-udp: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && tmon tmon.toml --transport udp

panel: $(PANEL_STAMP)

panel/.venv:
	python3 -m venv panel/.venv

$(PANEL_STAMP): panel/.venv panel/pyproject.toml server/pyproject.toml
	. panel/.venv/bin/activate && pip install -e server -e "panel/.[test]"
	touch $(PANEL_STAMP)

check: check-server check-firmware check-integration check-panel

check-server: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && pytest -m "not integration"

check-firmware:
	if command -v pio >/dev/null 2>&1; then cd client && pio test -e native; \
	else echo "pio not found, skipping firmware tests"; fi

check-integration: $(SERVER_STAMP)
	cd server && . .venv/bin/activate && pytest -m integration -v

check-panel: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && pytest

generate-panel-mock-data: $(PANEL_STAMP)
	cd panel && . .venv/bin/activate && python generate_data.py

run-panel: generate-panel-mock-data
	@echo "Starting panel at http://localhost:5000"
	cd panel && . .venv/bin/activate && TMON_DB=tmon_mock.db flask --app app run

# ---- Firmware ----
# Build generic firmware binaries (one per transport mode) and collect
# in firmware/.  Config is patched into the binary at flash time by
# tmon-patch, so no per-address builds are needed.

BOOT_APP0 := $(shell find ~/.platformio/packages/framework-arduinoespressif32 \
               -name boot_app0.bin 2>/dev/null | head -1)

firmware-485:
	cd client && pio run -e uart

firmware-udp:
	cd client && pio run -e udp

firmware: firmware-485 firmware-udp
	mkdir -p firmware
	cp client/.pio/build/uart/firmware.bin firmware/firmware-serial.bin
	cp client/.pio/build/udp/firmware.bin firmware/firmware-udp.bin
	cp client/.pio/build/uart/bootloader.bin firmware/bootloader.bin
	cp client/.pio/build/uart/partitions.bin firmware/partitions.bin
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

purge:
	deploy/uninstall.sh --purge

TAGS:
	find . -name '*.c' -o -name '*.cpp' -o -name '*.h' -o -name '*.py' | etags -

clean:
	rm -rf firmware server/.venv panel/.venv panel/tmon_mock.db
	if command -v pio >/dev/null 2>&1; then cd client && pio run -t clean; fi
