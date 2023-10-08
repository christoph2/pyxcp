#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
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
from pyxcp.recorder import UnfoldingParameters
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
            key_byte = processor.get("keyByte")
            header_len = DAQ_ID_FIELD_SIZE[key_byte["identificationField"]]
            max_dto = self.xcp_master.slaveProperties.maxDto
            max_odt_entry_size = resolution.get("maxOdtEntrySizeDaq")
            max_payload_size = min(max_odt_entry_size, max_dto - header_len)
            self.min_daq = processor.get("minDaq")
        except Exception as e:
            raise TypeError(f"DAQ_INFO corrupted: {e}") from e

        # DAQ optimization.
        for daq_list in self.daq_lists:
            ttt = make_continuous_blocks(daq_list.measurements, max_payload_size)
            daq_list.measurements_opt = first_fit_decreasing(ttt, max_payload_size)

        byte_order = 0 if self.xcp_master.slaveProperties.byteOrder == "INTEL" else 1
        self.uf = UnfoldingParameters(byte_order, header_len, self.ts_scale_factor, False, self.ts_size, self.daq_lists)

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
            # self.xcp_master.setDaqListMode(daqListNumber=i, mode=0x10, eventChannelNumber=daq_list.event_num, prescaler=1, priority=0xff)
            measurements = daq_list.measurements_opt
            for j, measurement in enumerate(measurements):
                self.xcp_master.setDaqPtr(i, j, 0)
                for entry in measurement.entries:
                    self.xcp_master.writeDaq(0xFF, entry.length, entry.ext, entry.address)

    def start(self):
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            mode = 0x10 if daq_list.enable_timestamps else 0x00
            self.xcp_master.setDaqListMode(
                daqListNumber=i, mode=mode, eventChannelNumber=daq_list.event_num, prescaler=1, priority=0xFF  # TODO: + MIN_DAQ
            )
            res = self.xcp_master.startStopDaqList(0x02, i)
            self.first_pids.append(res.firstPid)
        self.xcp_master.startStopSynch(0x01)

    def stop(self):
        self.xcp_master.startStopSynch(0x00)

    def reader(self):
        unfolder = XcpLogFileUnfolder(self.file_name, self.uf)
        unfolder.start(self.first_pids)

        for block in unfolder.next_block():
            print(block)


class Collector:
    def __init__(self, daq_num: int, num_odts: int, unfolder, callback):
        self.daq_num = daq_num
        self.num_odts = num_odts
        self.current_odt_num = 0
        self.frames = [None] * num_odts
        self.unfolder = unfolder
        self.callback = callback

    def add(self, odt_num, frame):
        if odt_num != self.current_odt_num:
            print(f"WRONG SEQ-NO {odt_num} expected {self.current_odt_num} [LIST: {self.daq_num}]")
            self.current_odt_num = odt_num
        self.frames[self.current_odt_num] = frame
        self.current_odt_num += 1
        if self.current_odt_num == self.num_odts:
            result = {}
            for idx, frame in enumerate(self.frames):
                offset = 0
                for name, length in self.unfolder[idx]:
                    data = frame[offset : offset + length]
                    result[name] = bytes(data)
                    offset += length
            if self.callback is not None:
                self.callback(0, result)
            # print("DAQ", self.daq_num, result)
        self.current_odt_num %= self.num_odts
