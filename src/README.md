# CircuitPython host application for the Cardputer

See top-level README file for instructions on how to use.

## Files in this folder:
- `code.py`: CircuitPython host application logic for the Cardputer. It reads commands from the keyboard, packs the inputs for the Calculator application, and prints and plots the results.
- `compute_module.py`: Integration with the Signaloid compute module. It detects whether a C0-microSD or a C0-microSD+ is in the microSD card slot, opens the matching `signaloid_utilities` interface, and runs commands through the compute module's input and output buffers.
- `settings.toml`: Configuration file for the CircuitPython application stack size.
- `assets/`: Images displayed by the host application.
- `lib/`: Created by `make bundle`. Holds the CircuitPython libraries:
  - `signaloid_utilities`: The SD-over-SPI interfaces to the Signaloid compute modules, compiled to `.mpy` files from the `Signaloid-Compute-Module-Utilities` submodule.
  - `signaloid`: Parsing and plotting of distributional values, compiled to `.mpy` files from the `signaloid-python` submodule.
  - `adafruit_display_text` and `circuitpython_uplot`: Display and plotting libraries, symlinked from the Adafruit and Community CircuitPython bundles.
  - `adafruit_ticks.mpy`: Needed by `adafruit_display_text`, symlinked from the Adafruit CircuitPython bundle.
