#   Copyright (c) 2026, Signaloid.
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

"""
Integration of a Signaloid compute module with a CircuitPython host.

This module detects which Signaloid compute module sits in the SD slot, opens
the matching interface of the `signaloid_utilities` package, and runs commands
on the device application through the module's input and output buffers. It
supports the C0-microSD and the C0-microSD+, both over SD-over-SPI.
"""

import time

from busio import SPI
from microcontroller import Pin

from signaloid_utilities.common.sd_over_spi_protocol import (
    SDOverSPI,
    SDOverSPIError,
)

C0_MICROSD = "C0-microSD"
C0_MICROSD_PLUS = "C0-microSD+"

# Each compute module's interface is imported only once that compute module is
# detected, because a microcontroller cannot spare the memory for both. So the
# values below are defined here rather than imported from an interface. They
# match `C0microSDInterface` and the status constants of `signaloid_utilities`.

# The C0-microSD reports its mode as a check word at this address.
C0_MICROSD_CONFIGURATION_STATUS_OFFSET = 0x20000
C0_MICROSD_SOC_CHECK_WORD = b"SSOC"
C0_MICROSD_BOOTLOADER_CHECK_WORD = b"SBLD"

# Values of the status register, shared by both compute modules
STATUS_WAITING_FOR_COMMAND = 0
STATUS_CALCULATING = 1
STATUS_DONE = 2
STATUS_INVALID_COMMAND = 3

# The command the host writes once a calculation finishes
COMMAND_IDLE = 0

POLL_INTERVAL_SECONDS = 0.01
START_TIMEOUT_SECONDS = 2.0
CALCULATION_TIMEOUT_SECONDS = 30.0


def detect_compute_module(spi: SPI, cs_pin: Pin, timeout: int) -> tuple:
    """
    Identifies the compute module in the SD slot, using reads only.

    The C0-microSD reports its mode as a check word in its configuration
    status register. The C0-microSD+ has a device identity tag instead. The
    status register is read first, because on the C0-microSD+ its address is
    an ordinary flash read (which returns zeros while the core runs), whereas
    the identity tag address is not mapped on the C0-microSD.

    :param spi: The SPI bus the compute module is on.
    :param cs_pin: The chip-select pin of the compute module.
    :param timeout: SD transaction timeout, in retries.

    :raises RuntimeError: when no supported compute module responds, or when
                          a C0-microSD is in Bootloader mode.

    :return: The name of the compute module (`C0_MICROSD` or
             `C0_MICROSD_PLUS`), and the class of its interface.
    """
    try:
        sd = SDOverSPI(spi=spi, cs_pin=cs_pin, timeout=timeout)
    except SDOverSPIError as error:
        raise RuntimeError(
            f"No compute module responds in the SD slot: {error}"
        )

    try:
        status = sd.read_blocks(C0_MICROSD_CONFIGURATION_STATUS_OFFSET, 1)
        check_word = bytes(status[0:4])
        if check_word == C0_MICROSD_SOC_CHECK_WORD:
            from signaloid_utilities.c0microsd.interface import (
                C0microSDSignaloidSoCInterfaceSDSPI as c0_microsd,
            )

            return C0_MICROSD, c0_microsd
        if check_word == C0_MICROSD_BOOTLOADER_CHECK_WORD:
            raise RuntimeError(
                "The C0-microSD is in Bootloader mode. "
                "Switch it to SoC mode and try again."
            )

        from signaloid_utilities.c0sd.interface import (
            C0microSDPlusInterfaceSDSPI as c0_microsd_plus,
        )

        identity_tag = c0_microsd_plus.IDENTITY_TAG
        identity = sd.read_blocks(
            c0_microsd_plus.DEFAULT_REGMAP.DeviceId.Identity0.ADDR, 1
        )
        if bytes(identity[0:len(identity_tag)]) == identity_tag:
            return C0_MICROSD_PLUS, c0_microsd_plus

        raise RuntimeError(
            "The card in the SD slot is not a C0-microSD or a C0-microSD+."
        )
    finally:
        # Release the chip-select pin, so that the interface of the detected
        # compute module can claim it.
        sd.cs.deinit()


def seconds_since(start_ns: int) -> float:
    """
    Returns the seconds elapsed since a `time.monotonic_ns()` timestamp.

    CircuitPython's `time.monotonic()` is a float that loses precision as
    the board's uptime grows, so time spans are measured in nanoseconds.

    :param start_ns: The start timestamp, from `time.monotonic_ns()`.

    :return: The elapsed time in seconds.
    """
    return (time.monotonic_ns() - start_ns) / 1000000000


class ComputeModule:
    """
    A Signaloid C0-microSD or C0-microSD+, driven over SD-over-SPI.

    Hides the differences between the two compute modules behind the calls a
    host application needs. Send the inputs and run a command with `run()`,
    then read the result with `interface.read_output_buffer()`.
    """

    def __init__(self, spi: SPI, cs_pin: Pin, timeout: int) -> None:
        """
        Detects the compute module, opens its interface, and makes sure the
        device application is waiting for a command.

        :param spi: The SPI bus the compute module is on.
        :param cs_pin: The chip-select pin of the compute module.
        :param timeout: SD transaction timeout, in retries.

        :raises RuntimeError: when no supported compute module responds, or
                              when the device application is not ready.
        """
        self.name, interface_class = detect_compute_module(
            spi, cs_pin, timeout
        )
        self.interface = interface_class(
            spi=spi, cs_pin=cs_pin, timeout=timeout
        )

        # The two interfaces name the status and command registers
        # differently.
        if self.name == C0_MICROSD:
            self._get_status = self.interface.get_signaloid_soc_status
            self._set_command = self.interface.send_signaloid_soc_command
        else:
            self._get_status = self.interface.get_status
            self._set_command = self.interface.set_command

        # Clear a command left by an interrupted run. The command register
        # keeps its value when the core restarts, and the device application
        # waits for the idle command before it accepts a new one.
        self._set_command(COMMAND_IDLE)
        if self.name == C0_MICROSD_PLUS:
            # The C0-microSD+ core keeps running across host restarts, so
            # restart it to begin from a known state.
            self.interface.reset_core(timeout=0.5)
        self._wait_until_idle("The device application is not ready.")

    def run(self, command: int, input_buffer: bytes) -> None:
        """
        Sends the inputs and runs a command. Read the result with
        `interface.read_output_buffer()`.

        :param command: The command value.
        :param input_buffer: The inputs, in the device application's format.

        :raises RuntimeError: when the device application is still busy with
                              a previous command, rejects the command, or
                              does not finish in time.
        """
        # A previous command that failed or timed out may still be running.
        # Its inputs must not be overwritten, and its status must not be
        # taken for the status of this command.
        self._wait_until_idle(
            "The device application is still busy with the previous command."
        )
        self.interface.write_input_buffer(input_buffer)
        self._set_command(command)
        try:
            self._wait_for_result()
        finally:
            # The device application waits for the idle command before it
            # accepts the next command.
            self._set_command(COMMAND_IDLE)
        self._wait_until_idle("The device application did not return to idle.")

    def _wait_for_result(self) -> None:
        """
        Polls the status register until the command finishes.

        :raises RuntimeError: when the command is rejected, does not start,
                              or does not finish in time.
        """
        start = time.monotonic_ns()
        while True:
            status = self._get_status()
            if status == STATUS_DONE:
                return
            if status == STATUS_INVALID_COMMAND:
                raise RuntimeError(
                    "The device application rejected the command."
                )
            if status == STATUS_WAITING_FOR_COMMAND:
                timeout = START_TIMEOUT_SECONDS
                message = (
                    "The device application did not start the command. "
                    "Check that it is flashed on the compute module."
                )
            elif status == STATUS_CALCULATING:
                timeout = CALCULATION_TIMEOUT_SECONDS
                message = "The calculation did not finish in time."
            else:
                raise RuntimeError(f"Unknown status: {status}")
            if seconds_since(start) > timeout:
                raise RuntimeError(message)
            time.sleep(POLL_INTERVAL_SECONDS)

    def _wait_until_idle(self, message: str) -> None:
        """
        Polls the status register until the device application waits for a
        command.

        :param message: The error message on timeout.

        :raises RuntimeError: when the device application does not become
                              idle in time.
        """
        start = time.monotonic_ns()
        while self._get_status() != STATUS_WAITING_FOR_COMMAND:
            if seconds_since(start) > START_TIMEOUT_SECONDS:
                raise RuntimeError(message)
            time.sleep(POLL_INTERVAL_SECONDS)
