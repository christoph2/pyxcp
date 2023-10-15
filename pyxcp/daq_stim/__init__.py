#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
import time
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from pprint import pprint
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from pyxcp import types
from pyxcp.cpp_ext import DaqList
from pyxcp.daq_stim.optimize import make_continuous_blocks
from pyxcp.daq_stim.optimize import McObject
from pyxcp.daq_stim.optimize.binpacking import first_fit_decreasing
from pyxcp.recorder import MeasurementParameters
from pyxcp.recorder import XcpLogFileReader
from pyxcp.recorder import XcpLogFileUnfolder
from pyxcp.types import FrameCategory


DAQ_ID_FIELD_SIZE = {
    "IDF_ABS_ODT_NUMBER": 1,
    "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_BYTE": 2,
    "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD": 3,
    "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD_ALIGNED": 4,
}

DAQ_TIMESTAMP_SIZE = {
    "S1": 1,
    "S2": 2,
    "S4": 4,
}


class Daq:
    def __init__(self, file_name: str, callback: Optional[Callable[[int, Tuple], None]] = None):
        self.callback = callback
        self.file_name = file_name

    def set_master(self, xcp_master):
        self.xcp_master = xcp_master

    def add_daq_lists(self, daq_lists: List[DaqList]):
        self.daq_lists = daq_lists

    def setup(self, write_multiple: bool = True):
        self.daq_info = self.xcp_master.getDaqInfo()
        pprint(self.daq_info)
        try:
            processor = self.daq_info.get("processor")
            properties = processor.get("properties")
            resolution = self.daq_info.get("resolution")
            if properties["configType"] == "STATIC":
                raise TypeError("DAQ configuration is static, cannot proceed.")
            self.supports_timestampes = properties["timestampSupported"]
            self.supports_prescaler = properties["prescalerSupported"]
            if self.supports_timestampes:
                mode = resolution.get("timestampMode")
                self.ts_fixed = mode.get("fixed")
                self.ts_size = DAQ_TIMESTAMP_SIZE[mode.get("size")]
                ts_unit_exp = types.DAQ_TIMESTAMP_UNIT_TO_EXP[mode.get("unit")]
                ts_ticks = resolution.get("timestampTicks")
                self.ts_scale_factor = (10**ts_unit_exp) * ts_ticks
            else:
                self.ts_size = 0
                self.ts_fixed = False
                self.ts_scale_factor = 0.0
            key_byte = processor.get("keyByte")
            header_len = DAQ_ID_FIELD_SIZE[key_byte["identificationField"]]
            max_dto = self.xcp_master.slaveProperties.maxDto
            self.min_daq = processor.get("minDaq")
            max_odt_entry_size = resolution.get("maxOdtEntrySizeDaq")
            max_payload_size = min(max_odt_entry_size, max_dto - header_len)
            # First ODT may contain timestamp.
            self.selectable_timestamps = False
            if not self.supports_timestampes:
                max_payload_size_first = max_payload_size
                print("NO TIMESTAMP SUPPORT")
            else:
                if self.ts_fixed:
                    print("Fixed timestamp")
                    max_payload_size_first = max_payload_size - self.ts_size
                else:
                    print("timestamp variable.")
                    self.selectable_timestamps = True

        except Exception as e:
            raise TypeError(f"DAQ_INFO corrupted: {e}") from e

        # DAQ optimization.
        for daq_list in self.daq_lists:
            if self.selectable_timestamps:
                if daq_list.enable_timestamps:
                    max_payload_size_first = max_payload_size - self.ts_size
                else:
                    max_payload_size_first = max_payload_size
            ttt = make_continuous_blocks(daq_list.measurements, max_payload_size, max_payload_size_first)
            daq_list.measurements_opt = first_fit_decreasing(ttt, max_payload_size, max_payload_size_first)
        byte_order = 0 if self.xcp_master.slaveProperties.byteOrder == "INTEL" else 1
        self.uf = MeasurementParameters(
            byte_order,
            header_len,
            self.supports_timestampes,
            self.ts_fixed,
            self.supports_prescaler,
            self.selectable_timestamps,
            self.ts_scale_factor,
            self.ts_size,
            self.min_daq,
            self.daq_lists,
        )

        self.first_pids = []
        daq_count = len(self.daq_lists)
        self.xcp_master.freeDaq()
        # Allocate
        self.xcp_master.allocDaq(daq_count)
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            measurements = daq_list.measurements_opt
            odt_count = len(measurements)
            self.xcp_master.allocOdt(i, odt_count)
            for j, measurement in enumerate(measurements):
                entry_count = len(measurement.entries)
                self.xcp_master.allocOdtEntry(i, j, entry_count)
        # Write DAQs
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            measurements = daq_list.measurements_opt
            for j, measurement in enumerate(measurements):
                self.xcp_master.setDaqPtr(i, j, 0)
                for entry in measurement.entries:
                    self.xcp_master.writeDaq(0xFF, entry.length, entry.ext, entry.address)

    def start(self):
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            mode = 0x00
            if self.supports_timestampes and (self.ts_fixed or (self.selectable_timestamps and daq_list.enable_timestamps)):
                mode = 0x10
            self.xcp_master.setDaqListMode(
                daqListNumber=i, mode=mode, eventChannelNumber=daq_list.event_num, prescaler=1, priority=0xFF  # TODO: + MIN_DAQ
            )
            res = self.xcp_master.startStopDaqList(0x02, i)
            self.first_pids.append(res.firstPid)
        self.xcp_master.startStopSynch(0x01)

    def stop(self):
        self.xcp_master.startStopSynch(0x00)

    import time

    def reader(self):
        unfolder = XcpLogFileUnfolder(self.file_name, self.uf)
        unfolder.start(self.first_pids)

        print("HEADERS")
        philez = []
        for idx, d in enumerate(self.daq_lists):
            philez.append(open(f"{d.name}.csv", "wt"))
            print(d.name, d.header_names)
            hdr = ",".join(["timestamp0", "timestamp1"] + d.header_names)
            philez[idx].write(f"{hdr}\n")
        print("DATA")
        start_time = time.perf_counter()
        for daq_list, ts0, ts1, payload in unfolder:
            philez[daq_list].write(f'{ts0},{ts1},{", ".join([str(x) for x in payload])}\n')
        for ph in philez:
            ph.close()
        print("ETA: ", time.perf_counter() - start_time, "seconds")
