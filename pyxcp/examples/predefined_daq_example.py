#!/usr/bin/env python3
"""
Example: Using Predefined DAQ-Lists in pyXCP

Predefined DAQ-lists are useful when the ECU already has a fixed ODT configuration
that does not need to be (or cannot be) programmed dynamically via XCP.

In this case, the master skips the ALLOC_DAQ, ALLOC_ODT, and WRITE_DAQ steps and
directly starts the DAQ list.
"""

from pyxcp.daq_stim import PredefinedDaqList, DaqToCsv
from pyxcp.cmdline import ArgumentParser


def predefined_daq_example():
    # Setup command line parser for common XCP options
    ap = ArgumentParser(description="Predefined DAQ-List Example")

    # We use the 'with' statement to ensure proper cleanup
    with ap.run() as xcp:
        print("Connecting...")
        xcp.connect()

        # Define the structure of the predefined ODTs on the slave.
        # Format: List of ODTs, where each ODT is a list of entries.
        # Each entry: (SignalName, DataType)
        # The addresses and offsets are already known to the slave.
        odt_config = [
            [
                ("EngineSpeed", "uint16"),
                ("EngineTemp", "int8"),
            ],
            [
                ("ThrottlePos", "uint8"),
            ],
        ]

        # Create the PredefinedDaqList instance.
        # Note: 'event_num' must match the event channel on the slave.
        daq_list = PredefinedDaqList(
            name="PredefinedList0", event_num=1, stim=False, enable_timestamps=True, odts=odt_config, priority=0, prescaler=1
        )

        print(f"Configured Predefined DAQ-List: {daq_list}")

        # Setup recording to CSV
        # The DaqProcessor (via DaqToCsv) will detect the PredefinedDaqList
        # and skip the dynamic programming steps.
        csv_policy = DaqToCsv([daq_list])

        print("Setting up DAQ...")
        xcp.setupDaq([daq_list], csv_policy)

        print("Starting DAQ for 5 seconds...")
        xcp.startDaq()

        import time

        time.sleep(5)

        print("Stopping DAQ...")
        xcp.stopDaq()
        xcp.disconnect()


if __name__ == "__main__":
    predefined_daq_example()
