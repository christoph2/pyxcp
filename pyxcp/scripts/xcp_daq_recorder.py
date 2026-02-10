#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""XCP DAQ list recorder."""

import argparse
import sys
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqRecorder, DaqToCsv, load_daq_lists_from_json  # noqa: F401
from pyxcp.types import XcpTimeoutError


def _get_config(config_path: Path) -> Dict[str, Any]:
    """Load configuration from a JSON file.

    Reads the JSON file at the given path and returns the deserialized content.
    In case of an error, an empty dict is returned and an error is logged.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        A dictionary with the configuration or an empty dict on error.
    """
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data
    except Exception as e:
        logging.error("Error loading config from %s: %s", config_path, e)
        return {}


def _parse_runtime(configuration: Dict[str, Any]) -> float:
    """Parse the runtime (runtime_seconds) from the configuration.

    If no value is present or the value is invalid, the default 60 seconds is returned.

    Args:
        configuration: The loaded configuration dictionary.

    Returns:
        Runtime in seconds as a float.
    """
    runtime_val = None
    if isinstance(configuration, dict):
        runtime_val = configuration.get("runtime_seconds")
    try:
        return float(runtime_val) if runtime_val is not None else 60.0
    except Exception:
        return 60.0


def _create_daq_parser(configuration: Dict[str, Any], daq_lists: list) -> Any:
    """Create the appropriate DAQ parser object based on the configuration.

    Args:
        configuration: The loaded configuration dictionary.
        daq_lists: The DAQ lists converted using load_daq_lists_from_json.

    Returns:
        An instance of DaqToCsv or DaqRecorder depending on 'output_type'.
    """
    output_type = "xmraw"
    # default filename gets current date/time: DDMMYYYY_HHMMSS
    default_output = f"run_daq_{datetime.now().strftime('%d%m%Y_%H%M%S')}"
    output_file = default_output
    if isinstance(configuration, dict):
        output_type = (configuration.get("output_type") or "xmraw").lower()
        output_file = configuration.get("output_file") or output_file

    if output_type == "csv":
        return DaqToCsv(daq_lists)
    return DaqRecorder(daq_lists, output_file, 8)


def main() -> None:
    """Main function: parse arguments, load config and start recording.

    The function is intentionally compact; helper functions handle parsing of
    runtime and creation of the DAQ parser.
    """
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="XCP DAQ list recorder")
    parser.add_argument(
        "DAQ_configuration_file",
        type=str,
        default=None,
    )

    ap = ArgumentParser(description="XCP DAQ list recorder", user_parser=parser)
    args = ap.args

    config_path = Path(args.DAQ_configuration_file).expanduser().resolve()
    if not config_path.exists():
        logging.error("DAQ configuration file %r does not exist.", str(config_path))
        sys.exit(1)

    configuration = _get_config(config_path)

    # Unterstütze sowohl neues Format {"daq_lists": [...]} als auch direktes List-Root.
    if isinstance(configuration, dict):
        daq_source = configuration.get("daq_lists", [])
    else:
        daq_source = configuration if configuration else []

    DAQ_LISTS = load_daq_lists_from_json(daq_source)

    runtime_seconds = _parse_runtime(configuration if isinstance(configuration, dict) else {})
    daq_parser = _create_daq_parser(configuration if isinstance(configuration, dict) else {}, DAQ_LISTS)

    with ap.run(policy=daq_parser) as x:
        try:
            x.connect()
        except XcpTimeoutError:
            sys.exit(2)

        if x.slaveProperties.optionalCommMode:
            x.getCommModeInfo()

        x.cond_unlock("DAQ")  # DAQ resource is locked in many cases.

        logging.info("setup DAQ lists.")
        daq_parser.setup()  # Execute setup procedures.
        logging.info("start DAQ lists.")
        daq_parser.start()  # Start DAQ lists.

        hours, remainder = divmod(runtime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        logging.info("Running DAQ for %02d:%02d:%02d (hh:mm:ss).", int(hours), int(minutes), int(seconds))
        if isinstance(daq_parser, DaqRecorder):
            print(f"Recording DAQ data to '{daq_parser.file_name}.xmraw'")
        time.sleep(runtime_seconds)
        logging.info("Stop DAQ....")
        daq_parser.stop()  # Stop DAQ lists.
        logging.info("finalize DAQ lists.")
        x.disconnect()

    if hasattr(daq_parser, "files"):  # `files` attribute is specific to `DaqToCsv`.
        logging.info("Data written to:")
        logging.info("================")
        for fl in daq_parser.files.values():
            logging.info(fl.name)


if __name__ == "__main__":
    main()
