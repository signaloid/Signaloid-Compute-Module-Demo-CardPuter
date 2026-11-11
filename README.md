# Signaloid Compute Module CardPuter CircuitPython Demo
This is a demo [CircuitPython](https://circuitpython.org/) host application on the [M5Stack CardPuter](https://docs.m5stack.com/en/core/CardPuter) for the [Signaloid Compute Module Calculator Demo](https://github.com/signaloid/Signaloid-Compute-Module-Demo-Calculator).

https://github.com/user-attachments/assets/15ec10e5-6ba8-48a0-8c9f-bce33e0dc572

This demo application supports the following arithmetic operations of two uniform distributions:
- Addition
- Subtraction
- Multiplication
- Division

## Compatibility
This demo supports the following Signaloid compute modules:
- **Signaloid C0-microSD**
- **Signaloid C0-microSD+**

The host application detects which compute module is in the CardPuter's microSD card slot when it starts, and uses the matching interface. You do not need to configure anything.

## Repository layout
Folder `src` contains the CircuitPython source code that runs on the CardPuter. The CardPuter acts as the host that communicates with the compute module through its integrated microSD card slot, over SD-over-SPI. See [`src/README.md`](src/README.md) for the files in it.

Folder `submodules/Signaloid-Compute-Module-Utilities/` contains the `signaloid_utilities` CircuitPython package, which defines the interface between the host and the compute module. `make bundle` compiles it to `.mpy` files in `src/lib/`.

Folder `submodules/signaloid-python/` contains the `signaloid` package, which defines the parsing and plotting of the distributional information from the compute module results. `make bundle` compiles its CircuitPython parts to `.mpy` files in `src/lib/`.

## Cloning this repository
The correct way to clone this repository is:
```sh
git clone --recursive https://github.com/signaloid/Signaloid-Compute-Module-Demo-CardPuter
```


If you forgot to clone with `--recursive`, and end up with empty submodule directories, you can remedy this with
```sh
git submodule update --init --recursive
```

## How to use:

### Build & Flash the compute module application
To build and flash the compute module application, follow the instructions in the [Signaloid Compute Module Calculator Demo](https://github.com/signaloid/Signaloid-Compute-Module-Demo-Calculator), with the `DEVICE_TYPE` variable set for your compute module:
- `SIGNALOID_C0_MICROSD` for the Signaloid C0-microSD. Leave the C0-microSD in SoC mode after flashing it.
- `SIGNALOID_C0_MICROSD_PLUS` for the Signaloid C0-microSD+.

This is **mandatory** before running the host application, so that the compute module runs the Calculator application, and is able to communicate with the host. Flash the compute module from a computer, and then move it to the CardPuter's microSD card slot.

### Prepare the CardPuter for the CircuitPython application
To prepare the CardPuter for the CircuitPython application, you have to flash it with the CircuitPython firmware following the instructions in the [CircuitPython M5Stack CardPuter documentation](https://circuitpython.org/board/m5stack_cardputer/).

> [!IMPORTANT]  
> Please use the `10.3.1` version of the CircuitPython firmware, which is the version this host application is tested with.  
> 
> Download the `10.3.1` version from [here](https://adafruit-circuit-python.s3.amazonaws.com/bin/m5stack_cardputer/en_US/adafruit-circuitpython-m5stack_cardputer-en_US-10.3.1.uf2), or use the `Browse S3` button from the [CircuitPython M5Stack CardPuter documentation](https://circuitpython.org/board/m5stack_cardputer/) and locate the `adafruit-circuitpython-m5stack_cardputer-en_US-10.3.1.uf2` file.

> [!NOTE]  
> 1. The guide needs to be run on the Google Chrome browser, it most likely won't work on other browsers (even Chromium-based ones).
> 2. Switch the CardPuter to its bootloader mode: Press and hold the `Btn G0` button, which is to the left of the `On/Off` switch, and then plug in the USB type-C cable to connect the CardPuter to your computer. Once connected, you can let the `Btn G0`. You will not see any reaction from the CardPuter (black screen, no LEDs). However, you should now be able to locate a new serial port device, typically `ttyACM0` on Linux, or `COM1` on Windows, or similar.
> 3. Click the `Open installer` button on the latest stable CircuitPython release section of the [CircuitPython M5Stack CardPuter documentation](https://circuitpython.org/board/m5stack_cardputer/).
> 4. Choose the `Install Bootloader only` option, and click next.
> 5. Click the `Connect` button, and choose your new serial port device. Click `Continue`, wait until the flashing finishes, and then click `Close`. This will erase everything on the CardPuter, and flash the latest bootloader. If no serial port selection window appears, make sure you are using the Chrome browser.
> 6. Reboot the CardPuter by pressing the `Btn Rst` button, at the back of the CardPuter.
> 7. You should now be able to see a new `FTHRS3BOOT` removable storage device. If you are using Linux, you have to mount it.
> 8. You may now close the installer.
> 9. Locate the `adafruit-circuitpython-m5stack_cardputer-en_US-10.3.1.uf2` file you previously downloaded, and copy it to the `FTHRS3BOOT` device. It should now reboot to the CircuitPython firmware.
> 10. You should now be able to see a `Hello World!` greeting on the CardPuter, and a `CIRCUITPY` removable storage device on your computer. If not, try to reboot the CardPuter by pressing the `Btn Rst` button.


### Run the CircuitPython based host application
To run the Python host application you first need to bundle all library dependencies. To do that run this command from the `root` folder:
```sh
make
```

This command will do the following:
1. Initialize & update all submodules.
2. Create the `CircuitPythonLibs/` folder, where the [Adafruit CircuitPython bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle) and the [Community CircuitPython bundle](https://github.com/adafruit/CircuitPython_Community_Bundle) libraries are downloaded and extracted, together with the CircuitPython `mpy-cross` compiler for your computer.
3. Create the `src/lib/` folder, where the bundle libraries are symlinked to, and where the Signaloid libraries are compiled to `.mpy` files. Compiled libraries take much less memory on the CardPuter than `.py` files, which the CardPuter would have to compile itself.

The `Makefile` downloads `mpy-cross` for Linux (x86-64, ARM64, and Raspberry Pi) and for macOS on Apple silicon. On other platforms, set the `MPY_CROSS_URL` variable to a `mpy-cross` build for CircuitPython `10.3.1`.

If you change a library in the `submodules` folder, run `make libraries` to compile the Signaloid libraries again, without cloning the submodules again.

### Copy the CircuitPython application to the CardPuter
To copy the CircuitPython application to the CardPuter, run this command from the `root` folder:
```sh
make sync
```
This command will hard copy all the files and folders from the `src` folder to the CardPuter. Make sure that you have mounted your CardPuter to your computer, and that the mount path is correctly specified at the `DEVICE` variable in the `Makefile` (default is `/run/media/<user>/CIRCUITPY`).

### Live sync the CircuitPython application to the CardPuter
To live sync the CircuitPython application to the CardPuter, while you are developing or making changes, run this command from the `root` folder:
```sh
make live-sync
```
This command will first sync all the files and folders from the `src` folder to the CardPuter, then watch for any changes in the `src` folder, and live sync them to the CardPuter. Make sure that you have mounted your CardPuter to your computer, and that the mount path is correctly specified at the `DEVICE` variable in the `Makefile` (default is `/run/media/<user>/CIRCUITPY`).

### Clean project
To clean the project, run this command from the `root` folder:
```sh
make clean
```
This command will delete the `CircuitPythonLibs/`, and the `src/lib/` folders.

### Clean the CardPuter
To clean the CardPuter, run this command from the `root` folder:
```sh
make clean-device
```
This command will delete all files and folders from the CardPuter, and will create a new "Hello World" `code.py` file. Make sure that you have mounted your CardPuter to your computer and that the mount path is correctly specified at the `DEVICE` variable in the `Makefile` (default is `/run/media/<user>/CIRCUITPY`).

## Host application
When it starts, the host application detects the compute module in the microSD card slot, prints its name, and starts its device application. It then parses commands with two input arguments. Each argument can be:
- A float, e.g. `1.5`.
- A uniform distribution, represented in the [concise form of uncertainty
notation](https://physics.nist.gov/cgi-bin/cuu/Info/Constants/definitions.html#:~:text=A%20more%20concise%20form%20of,digits%20of%20the%20quoted%20result.&text=See%20Uncertainty%20of%20Measurement%20Results), i.e., `X.Y(Z)`.
- A [Ux string](https://docs.signaloid.io/docs/uxhw-api/ux-data-format/).

The application supports addition, subtraction, multiplication, and division of the input arguments.
```
usage: {add,sub,mul,div} A B

Host application for the Signaloid Compute Module Calculator Demo application

positional arguments:
  {add,sub,mul,div}
                        Commands
    add                 Add A and B
    sub                 Subtract B from A
    mul                 Multiply A and B
    div                 Divide A by B

    A B                 Two floats, uniform distributions in the X.Y(Z) form,
                        or Ux strings
```

For example, you can multiply the value `2.0` with a tolerance of `+- 0.5` and the value `5.0` with a tolerance of `+- 0.3` by running:

```sh
mul 2.0(5) 5.0(3)
```

Enter `q` after a calculation to exit.

### How the CardPuter connects to the compute module
The CardPuter's microSD card slot is wired to the ESP32-S3 as an SPI bus, which CircuitPython provides as `board.SD_SPI()`. The host application drives the compute module over that bus with SD-over-SPI, in SPI mode 0 at 5 MHz.

| SD-over-SPI signal | Compute module pad | CircuitPython pin | ESP32-S3 GPIO |
| ------------------ | ------------------ | ----------------- | ------------- |
| SCLK               | CLK                | `board.SD_SCK`    | GPIO40        |
| MOSI               | CMD                | `board.SD_MOSI`   | GPIO14        |
| MISO               | DAT0               | `board.SD_MISO`   | GPIO39        |
| CS                 | DAT3               | `board.SD_CS`     | GPIO12        |

The compute module integration code is in [`src/compute_module.py`](src/compute_module.py). It detects the compute module variant, and runs commands through the module's input and output buffers.
