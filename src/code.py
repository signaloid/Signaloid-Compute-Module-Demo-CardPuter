#   Copyright (c) 2024, Signaloid.
#
#   Permission is hereby granted, free of charge, to any person obtaining a
#   copy of this software and associated documentation files (the "Software"),
#   to deal in the Software without restriction, including without limitation
#   the rights to use, copy, modify, merge, publish, distribute, sublicense,
#   and/or sell copies of the Software, and to permit persons to whom the
#   Software is furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#   FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.


import gc
import struct

import board
import busio
from microcontroller import Pin

from compute_module import ComputeModule
from signaloid.circuitpython.plot_wrapper import plot
from signaloid.distributional.dirac_delta import DiracDelta
from signaloid.distributional.distributional import DistributionalValue
from signaloid.distributional_information_plotting import (
    plot_histogram_dirac_deltas,
)


class APP_CONFIG:
    """Application configuration.

    This class contains the configuration for the application, including the
    chip-select pin of the SD slot and the SPI baudrate.
    """
    PIN_SD_CS: Pin = board.SD_CS
    SPI_BAUDRATE: int = 5000000
    SD_REPEAT_TIMEOUT: int = 1000
    DOUBLE_PRECISION: bool = False
    PLOTTING_RESOLUTION: int = 32


kCalculateAddition = 1
kCalculateSubtraction = 2
kCalculateMultiplication = 3
kCalculateDivision = 4

calculation_commands = {
    "add": kCalculateAddition,
    "sub": kCalculateSubtraction,
    "mul": kCalculateMultiplication,
    "div": kCalculateDivision,
}

USAGE = (
    "Usage: <add|sub|mul|div> <A> <B>\n"
    "A and B are floats (1.5), values with uncertainty (2.0(5)),\n"
    "or Ux strings."
)


def init_spi() -> busio.SPI:
    """
    Initializes the SPI bus of the SD slot.

    SD-over-SPI uses SPI mode 0, the default of `configure()`. The SD driver
    of `signaloid_utilities` identifies the card at 400 kHz, and then returns
    the bus to the baudrate set here.

    :return: The configured SPI bus.
    """
    spi = board.SD_SPI()
    while not spi.try_lock():
        pass
    spi.configure(baudrate=APP_CONFIG.SPI_BAUDRATE)
    spi.unlock()
    return spi


def parse_tolerance_value(value_with_uncertainty: str) -> tuple[float, float]:
    """
    This function parses a string following the concise form of uncertainty
    notation 'X.Y(Z)' to create a uniform distribution, whose minimum and
    maximum values are returned as a tuple.

    For more information on the concise form of uncertainty notation, see:
    https://physics.nist.gov/cgi-bin/cuu/Info/Constants/definitions.html#:~:text=A%20more%20concise%20form%20of,digits%20of%20the%20quoted%20result.&text=See%20Uncertainty%20of%20Measurement%20Results

    :param  value_with_uncertainty: the string to parse

    :raises ValueError: when the input string is not in the correct format

    :return: minimum and maximum values of the uniform distribution
    """

    # Split the value and the uncertainty part
    if '(' not in value_with_uncertainty or ')' not in value_with_uncertainty:
        raise ValueError(
            "Invalid format. Please provide value in the format 'X.Y(Z)'")

    # Extract the main value and the uncertainty
    value_str, uncertainty_str = value_with_uncertainty.split('(')
    uncertainty_str = uncertainty_str.strip(')')

    # Find smallest order
    if "." in value_str:
        # Split at the decimal point
        _, decimal_part = value_str.split(".")
        order = -(len(decimal_part))
    else:
        order = 0

    # Convert to appropriate types
    value = float(value_str)
    uncertainty = int(uncertainty_str)

    # Calculate minimum and maximum values
    min_value = value - (uncertainty * (10 ** order))
    max_value = value + (uncertainty * (10 ** order))

    return (min_value, max_value)


def value_to_bytes(value: str, double_precision: bool) -> bytes:
    """
    Converts one input value to the bytes the Calculator application expects.

    :param value: A float ("1.5"), a value with uncertainty in the concise
                  form "X.Y(Z)", or a Ux string.
    :param double_precision: If distributions use double precision positions.

    :raises ValueError: when the value cannot be parsed.

    :return: A single-precision float, or Ux binary data.
    """
    if "Ux" in value:
        distribution = DistributionalValue.parse(value)
        if distribution is None:
            raise ValueError(f"Cannot parse Ux string: {value}")
        return bytes(distribution)

    if "(" in value:
        # The Calculator application treats an input with two equally
        # weighted Dirac deltas, at the minimum and the maximum, as a uniform
        # distribution between them.
        min_value, max_value = parse_tolerance_value(value)
        distribution = DistributionalValue(
            particle_value=(min_value + max_value) / 2,
            dirac_deltas=[
                DiracDelta(position=min_value, mass=0.5),
                DiracDelta(position=max_value, mass=0.5),
            ],
            double_precision=double_precision,
        )
        return bytes(distribution)

    return struct.pack("<f", float(value))


def build_input_buffer(values: list[str], double_precision: bool) -> bytes:
    """
    Packs the input values in the format of the Calculator application.

    The format is a uint32 count of values, followed by a uint32 size and the
    bytes of each value.

    :param values: The input values, see `value_to_bytes`.
    :param double_precision: If distributions use double precision positions.

    :return: The input buffer.
    """
    buffer = struct.pack("<I", len(values))
    for value in values:
        value_bytes = value_to_bytes(value, double_precision)
        buffer += struct.pack("<I", len(value_bytes)) + value_bytes
    return buffer


def read_result(compute_module: ComputeModule) -> bytes:
    """
    Reads the result of the Calculator application.

    The Calculator application writes a uint32 count of values (one), then
    the uint32 size and the bytes of the value. Reading less than an SD block
    takes the same transfer as reading a whole block, so the first read takes
    one block, and a second read follows only for a longer result.

    :param compute_module: The compute module that ran the calculation.

    :raises RuntimeError: when the Calculator application returned no values.

    :return: The bytes of the value, in Ux binary format.
    """
    interface = compute_module.interface
    result = interface.read_output_buffer(interface.sd.block_size)
    count, size = struct.unpack("<II", result[0:8])
    if count == 0:
        raise RuntimeError(
            "The Calculator application returned no values. "
            "Check the inputs."
        )
    if 8 + size > len(result):
        result = interface.read_output_buffer(8 + size)
    return result[8:8 + size]


def main():
    # Clear the screen
    print("\n"*10)

    # Get the default display root group (the terminal), so that we can
    # restore it later
    default_display_root_group = board.DISPLAY.root_group

    # Detect the compute module in the SD slot and start its device
    # application. Exit if there is no supported compute module.
    try:
        compute_module = ComputeModule(
            spi=init_spi(),
            cs_pin=APP_CONFIG.PIN_SD_CS,
            timeout=APP_CONFIG.SD_REPEAT_TIMEOUT,
        )
    except Exception as e:
        print(e)
        return

    print(f"Found a Signaloid {compute_module.name}.")
    print(USAGE)

    # Main loop: Continue to ask for commands until the user enters 'q'
    while True:
        try:
            print("\n"*2)

            # Ask the user for a command
            command = input("Give me a command...\n")
            arguments = command.split()
            if len(arguments) != 3 or arguments[0] not in calculation_commands:
                raise ValueError(USAGE)

            input_buffer = build_input_buffer(
                arguments[1:],
                double_precision=APP_CONFIG.DOUBLE_PRECISION,
            )

            print(f"Calculating on the {compute_module.name}...")
            compute_module.run(
                calculation_commands[arguments[0]], input_buffer
            )

            print("Parsing distribution.")
            distribution = DistributionalValue.parse(
                read_result(compute_module),
                double_precision=APP_CONFIG.DOUBLE_PRECISION,
            )

            if distribution is None:
                print("Cannot parse resulting Ux bytes.")
            else:
                print(distribution)

                print(f"Plotting {command}")
                plot(
                    plot_data=plot_histogram_dirac_deltas.PlotData(
                        distribution,
                        plotting_resolution=APP_CONFIG.PLOTTING_RESOLUTION,
                    ),
                    plot_name=command
                )
        except Exception as e:
            print(
                f"An error occurred while calculating: \n{e} \nAborting.",
            )

        # Ask the user to press Enter to continue, or 'q' to exit
        res = input("Press Enter to continue, or q to exit...")

        # Restore the default display root group (the terminal)
        board.DISPLAY.root_group = default_display_root_group

        # Free the plot right away. CircuitPython grows its heap in separate
        # areas and returns an area to the system only once it is empty. If
        # the plot stayed uncollected, the objects of the next command could
        # land in the area that holds it, and keep that memory from the next
        # plot. After a few plots, there would be no memory left for one.
        gc.collect()

        if res == 'q':
            return


if __name__ == "__main__":
    main()
