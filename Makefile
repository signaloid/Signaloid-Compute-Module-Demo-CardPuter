# Copyright (c) 2024, Signaloid.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.


# The CircuitPython device mount path to sync the host application.
DEVICE := /run/media/$(shell whoami)/CIRCUITPY

# Adafruit and Community CircuitPython library bundles.
# To use a different bundle version, just change the version numbers below.
CIRCUITPYTHON_ADAFRUIT_BUNDLE_VERSION 	:= 20261003
CIRCUITPYTHON_ADAFRUIT_BUNDLE_NAME 	:= adafruit-circuitpython-bundle-10.x-mpy-$(CIRCUITPYTHON_ADAFRUIT_BUNDLE_VERSION)
CIRCUITPYTHON_ADAFRUIT_BUNDLE_URL 	:= https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/download/$(CIRCUITPYTHON_ADAFRUIT_BUNDLE_VERSION)/$(CIRCUITPYTHON_ADAFRUIT_BUNDLE_NAME).zip

CIRCUITPYTHON_COMMUNITY_BUNDLE_VERSION 	:= 20260923
CIRCUITPYTHON_COMMUNITY_BUNDLE_NAME 	:= circuitpython-community-bundle-10.x-mpy-$(CIRCUITPYTHON_COMMUNITY_BUNDLE_VERSION)
CIRCUITPYTHON_COMMUNITY_BUNDLE_URL 	:= https://github.com/adafruit/CircuitPython_Community_Bundle/releases/download/$(CIRCUITPYTHON_COMMUNITY_BUNDLE_VERSION)/$(CIRCUITPYTHON_COMMUNITY_BUNDLE_NAME).zip

# The CircuitPython version the host application runs on. Its mpy-cross
# compiles the Signaloid libraries to .mpy files, because compiling the .py
# files on the CardPuter takes more memory than the CardPuter can spare.
CIRCUITPYTHON_VERSION 	:= 10.3.1
MPY_CROSS_URL_PREFIX 	:= https://adafruit-circuit-python.s3.amazonaws.com/bin/mpy-cross
MPY_CROSS_PLATFORM 	:= $(shell uname -s)-$(shell uname -m)
ifeq ($(MPY_CROSS_PLATFORM),Linux-x86_64)
MPY_CROSS_URL := $(MPY_CROSS_URL_PREFIX)/linux-amd64/mpy-cross-linux-amd64-$(CIRCUITPYTHON_VERSION).static
else ifeq ($(MPY_CROSS_PLATFORM),Linux-aarch64)
MPY_CROSS_URL := $(MPY_CROSS_URL_PREFIX)/linux-aarch64/mpy-cross-linux-aarch64-$(CIRCUITPYTHON_VERSION).static-aarch64
else ifeq ($(MPY_CROSS_PLATFORM),Linux-armv7l)
MPY_CROSS_URL := $(MPY_CROSS_URL_PREFIX)/linux-raspbian/mpy-cross-linux-raspbian-$(CIRCUITPYTHON_VERSION).static-raspbian
else ifeq ($(MPY_CROSS_PLATFORM),Darwin-arm64)
MPY_CROSS_URL := $(MPY_CROSS_URL_PREFIX)/macos/mpy-cross-macos-$(CIRCUITPYTHON_VERSION)-arm64
endif

# The Signaloid library packages that run on CircuitPython, as
# <directory>:<package> pairs, relative to the submodules folder.
SIGNALOID_LIBRARIES := \
	Signaloid-Compute-Module-Utilities/src/circuitpython:signaloid_utilities \
	signaloid-python/src:signaloid/circuitpython \
	signaloid-python/src:signaloid/distributional \
	signaloid-python/src:signaloid/distributional_information_plotting


# Acquire the project root directory, used to locate all other directories.
MAKEFILE_PATH 	:= $(abspath $(firstword $(MAKEFILE_LIST)))
MAKEFILE_DIR 	:= $(dir $(MAKEFILE_PATH))
ROOT_DIR 	:= $(abspath $(MAKEFILE_DIR))

# Define the CircuitPython library directory, where the CircuitPython libraries
# are downloaded and extracted.
CIRCUITPYTHON_LIBS_DIR := $(ROOT_DIR)/CircuitPythonLibs
MPY_CROSS := $(CIRCUITPYTHON_LIBS_DIR)/mpy-cross

# The host application source directory, where all the host application source
# code, libraries, and assets are located.
SRC_DIR := $(ROOT_DIR)/src


.PHONY: bundle libraries sync live-sync clean clean-device

all: bundle

# Bundle the host application and CircuitPython libraries.
bundle: clean
	@echo "Bundling files to project"
	rm -rf $(ROOT_DIR)/submodules/Signaloid-Compute-Module-Utilities
	rm -rf $(ROOT_DIR)/submodules/signaloid-python
	git submodule update --init --recursive
	@test -n "$(MPY_CROSS_URL)" || { echo "No CircuitPython mpy-cross for $(MPY_CROSS_PLATFORM). Set MPY_CROSS_URL to one from $(MPY_CROSS_URL_PREFIX)/"; exit 1; }
	mkdir -p $(CIRCUITPYTHON_LIBS_DIR)
	cd $(CIRCUITPYTHON_LIBS_DIR) && \
	wget $(CIRCUITPYTHON_ADAFRUIT_BUNDLE_URL) && \
	wget $(CIRCUITPYTHON_COMMUNITY_BUNDLE_URL) && \
	wget -O $(MPY_CROSS) $(MPY_CROSS_URL) && \
	chmod +x $(MPY_CROSS) && \
	unzip -o $(CIRCUITPYTHON_ADAFRUIT_BUNDLE_NAME).zip && \
	unzip -o $(CIRCUITPYTHON_COMMUNITY_BUNDLE_NAME).zip
	mkdir -p $(ROOT_DIR)/src/lib
	cd $(ROOT_DIR)/src/lib && \
	ln -s $(CIRCUITPYTHON_LIBS_DIR)/$(CIRCUITPYTHON_ADAFRUIT_BUNDLE_NAME)/lib/adafruit_display_text && \
	ln -s $(CIRCUITPYTHON_LIBS_DIR)/$(CIRCUITPYTHON_ADAFRUIT_BUNDLE_NAME)/lib/adafruit_ticks.mpy && \
	ln -s $(CIRCUITPYTHON_LIBS_DIR)/$(CIRCUITPYTHON_COMMUNITY_BUNDLE_NAME)/lib/circuitpython_uplot
	$(MAKE) libraries

# Compile the Signaloid libraries to .mpy files in src/lib. Run it again after
# changing a library in the submodules.
libraries:
	@echo "Compiling the Signaloid libraries to .mpy files"
	rm -rf $(ROOT_DIR)/src/lib/signaloid_utilities $(ROOT_DIR)/src/lib/signaloid
	for library in $(SIGNALOID_LIBRARIES); do \
		( cd $(ROOT_DIR)/submodules/$${library%%:*} && \
		find -L $${library#*:} -name '*.py' -not -name '*_test.py' | \
		while read -r file; do \
			mkdir -p $(ROOT_DIR)/src/lib/$$(dirname $$file) && \
			$(MPY_CROSS) -o $(ROOT_DIR)/src/lib/$${file%.py}.mpy $$file || exit 1; \
		done ) || exit 1; \
	done

# Sync the host application and CircuitPython libraries to the device.
sync: clean-device
	@echo "Syncing files to $(DEVICE)"
	@cd $(ROOT_DIR)/src/ && \
	find -L . \
	-type d \
	-exec mkdir -pv '$(DEVICE)/{}' ';'

	@cd $(ROOT_DIR)/src/ && \
	find -L . \
	-type f \
	-not -iname "*.md" \
	-not -iname "py.typed" \
	-not -iname "*.csv" \
	-not -iname "*_test.py" \
	-not -iname ".DS_Store" \
	-exec cp -Lrv '{}' '$(DEVICE)/{}' ';'


# Sync the host application and CircuitPython libraries to the device, and
# watch for any changes in the host application source code, and live sync them
# to the device.
live-sync: sync
	@echo "Live Syncing files to $(DEVICE)"
	@inotifywait -m -r -e create,close_write,moved_from,moved_to --format '%e %w%f' $(SRC_DIR) | \
	while read EVENT FILE_PATH; do \
	NEW_FILE_PATH="$(DEVICE)$${FILE_PATH/"$(SRC_DIR)"/""}"; \
	if [ $$EVENT = "CREATE,ISDIR" ]; then \
		echo "  MKDIR $$NEW_FILE_PATH"; \
		mkdir -p $$NEW_FILE_PATH; \
	elif [ $$EVENT = "MOVED_FROM" ] || [ $$EVENT = "MOVED_FROM,ISDIR" ]; then \
		echo "  RM    $$NEW_FILE_PATH"; \
		rm -rf $$NEW_FILE_PATH; \
	elif [ $$EVENT = "CLOSE_WRITE,CLOSE" ] || [ $$EVENT = "MOVED_TO" ] || [ $$EVENT = "MOVED_TO,ISDIR" ]; then \
		echo "  CP    $$NEW_FILE_PATH"; \
		cp -r $$FILE_PATH $$NEW_FILE_PATH; \
	elif [ $$EVENT = "CREATE" ]; then \
		: \
	else \
		echo "  Unhandled event $$EVENT for $$FILE_PATH"; \
	fi; \
	done;

live-sync-mac: sync
	@echo "Live Syncing files to $(DEVICE)"
	@fswatch -nr $(SRC_DIR) | \
	while read FILE_PATH EVENT; do \
	FILENAME=$$(sed 's+$(SRC_DIR)++g' <<< $$FILE_PATH); \
	NEW_FILE_PATH="$(DEVICE)$$FILENAME";\
	if [ $$EVENT = "1026" ]; then \
		echo "  MKDIR $$NEW_FILE_PATH"; \
		mkdir -p $$NEW_FILE_PATH; \
	elif [ $$EVENT = "580" ]; then \
		echo "  CP    $$NEW_FILE_PATH"; \
		cp -r $$FILE_PATH $$NEW_FILE_PATH; \
	elif [ $$EVENT = "514" ]; then \
		echo "  TOUCH $$NEW_FILE_PATH"; \
		touch $$NEW_FILE_PATH; \
	else \
		echo "  Unhandled event $$EVENT for $$FILE_PATH"; \
	fi; \
	done;

# Clean the project.
clean:
	rm -rf $(CIRCUITPYTHON_LIBS_DIR)
	rm -rf $(ROOT_DIR)/src/lib
	rm -rf $(ROOT_DIR)/submodules/*/

# Clean the device.
clean-device:
	rm -rf $(DEVICE)/*
	@echo "print(\"Hello World!\")" > $(DEVICE)/code.py
