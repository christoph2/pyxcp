#!/usr/bin/env python

# from pprint import pprint
from time import time_ns
from typing import Dict, List, TextIO

from pyxcp import types
from pyxcp.config import get_application
from pyxcp.cpp_ext import DaqList
from pyxcp.daq_stim.optimize import make_continuous_blocks
from pyxcp.daq_stim.optimize.binpacking import first_fit_decreasing
from pyxcp.recorder import DaqOnlinePolicy as _DaqOnlinePolicy
from pyxcp.recorder import DaqRecorderPolicy as _DaqRecorderPolicy
from pyxcp.recorder import MeasurementParameters
from pyxcp.utils import CurrentDatetime


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


class DaqProcessor:
    def __init__(self, daq_lists: List[DaqList]):
        # super().__init__()
        self.daq_lists = daq_lists
        self.log = get_application().log

    def setup(self, start_datetime: CurrentDatetime | None = None, write_multiple: bool = True):
        self.daq_info = self.xcp_master.getDaqInfo()
        if start_datetime is None:
            start_datetime = CurrentDatetime(time_ns())
        self.start_datetime = start_datetime
        # print(self.start_datetime)
        try:
            processor = self.daq_info.get("processor")
            properties = processor.get("properties")
            resolution = self.daq_info.get("resolution")
            if properties["configType"] == "STATIC":
                raise TypeError("DAQ configuration is static, cannot proceed.")
            self.supports_timestampes = properties["timestampSupported"]
            self.supports_prescaler = properties["prescalerSupported"]
            self.supports_pid_off = properties["pidOffSupported"]
            if self.supports_timestampes:
                mode = resolution.get("timestampMode")
                self.ts_fixed = mode.get("fixed")
                self.ts_size = DAQ_TIMESTAMP_SIZE[mode.get("size")]
                ts_factor = types.DAQ_TIMESTAMP_UNIT_TO_NS[mode.get("unit")]
                ts_ticks = resolution.get("timestampTicks")
                self.ts_scale_factor = ts_factor * ts_ticks
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
                # print("NO TIMESTAMP SUPPORT")
            else:
                if self.ts_fixed:
                    # print("Fixed timestamp")
                    max_payload_size_first = max_payload_size - self.ts_size
                else:
                    # print("timestamp variable.")
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
        self._first_pids = []
        daq_count = len(self.daq_lists)
        self.xcp_master.freeDaq()

        # Allocate
        self.xcp_master.allocDaq(daq_count)
        measurement_list = []
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            measurements = daq_list.measurements_opt
            measurement_list.append((i, measurements))
            odt_count = len(measurements)
            self.xcp_master.allocOdt(i, odt_count)
        # Iterate again over ODT entries -- we need to respect sequencing requirements.
        for i, measurements in measurement_list:
            for j, measurement in enumerate(measurements):
                entry_count = len(measurement.entries)
                self.xcp_master.allocOdtEntry(i, j, entry_count)
        # Write DAQs
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            measurements = daq_list.measurements_opt
            for j, measurement in enumerate(measurements):
                if len(measurement.entries) == 0:
                    continue  # CAN special case: No room for data in first ODT.
                self.xcp_master.setDaqPtr(i, j, 0)
                for entry in measurement.entries:
                    self.xcp_master.writeDaq(0xFF, entry.length, entry.ext, entry.address)

        # arm DAQ lists -- this is technically a function on its own.
        for i, daq_list in enumerate(self.daq_lists, self.min_daq):
            # print(daq_list.name, daq_list.event_num, daq_list.stim)
            mode = 0x00
            if self.supports_timestampes and (self.ts_fixed or (self.selectable_timestamps and daq_list.enable_timestamps)):
                mode = 0x10
            if daq_list.stim:
                mode |= 0x02
            ###
            ## mode |= 0x20
            ###
            self.xcp_master.setDaqListMode(
                daqListNumber=i, mode=mode, eventChannelNumber=daq_list.event_num, prescaler=1, priority=0xFF
            )
            res = self.xcp_master.startStopDaqList(0x02, i)
            self._first_pids.append(res.firstPid)
        if start_datetime:
            pass
        self.measurement_params = MeasurementParameters(
            byte_order,
            header_len,
            self.supports_timestampes,
            self.ts_fixed,
            self.supports_prescaler,
            self.selectable_timestamps,
            self.ts_scale_factor,
            self.ts_size,
            self.min_daq,
            self.start_datetime,
            self.daq_lists,
            self._first_pids,
        )
        self.set_parameters(self.measurement_params)

    def start(self):
        self.xcp_master.startStopSynch(0x01)

    def stop(self):
        self.xcp_master.startStopSynch(0x00)

    def first_pids(self):
        return self._first_pids


class DaqRecorder(DaqProcessor, _DaqRecorderPolicy):

    def __init__(self, daq_lists: List[DaqList], file_name: str, prealloc: int = 200, chunk_size: int = 1):
        DaqProcessor.__init__(self, daq_lists)
        _DaqRecorderPolicy.__init__(self)
        self.file_name = file_name
        self.prealloc = prealloc
        self.chunk_size = chunk_size

    def initialize(self):
        metadata = self.measurement_params.dumps()
        _DaqRecorderPolicy.create_writer(self, self.file_name, self.prealloc, self.chunk_size, metadata)
        _DaqRecorderPolicy.initialize(self)

    def finalize(self):
        _DaqRecorderPolicy.finalize(self)

    def start(self):
        DaqProcessor.start(self)


class DaqOnlinePolicy(DaqProcessor, _DaqOnlinePolicy):
    """Base class for on-line measurements.
    Handles multiple inheritence.
    """

    def __init__(self, daq_lists: List[DaqList]):
        DaqProcessor.__init__(self, daq_lists)
        _DaqOnlinePolicy.__init__(self)

    def start(self):
        DaqProcessor.start(self)


class DaqToCsv(DaqOnlinePolicy):
    """Save a measurement as CSV files (one per DAQ-list)."""

    def initialize(self):
        self.log.debug("DaqCsv::Initialize()")
        self.files: Dict[int, TextIO] = {}
        for num, daq_list in enumerate(self.daq_lists):
            if daq_list.stim:
                continue
            out_file = open(f"{daq_list.name}.csv", "w")
            self.files[num] = out_file
            hdr = ",".join(["timestamp0", "timestamp1"] + [h[0] for h in daq_list.headers])
            out_file.write(f"{hdr}\n")

    def on_daq_list(self, daq_list: int, ts0: int, ts1: int, payload: list):
        self.files[daq_list].write(f"{ts0},{ts1},{', '.join([str(x) for x in payload])}\n")

    def finalize(self):
        self.log.debug("DaqCsv::finalize()")
        ##
        ## NOTE: `finalize` is guaranteed to be called, but `Initialize` may fail for reasons.
        ##       So if you allocate resources in `Initialize` check if this really happened.
        ##
        if hasattr(self, "files"):
            for f in self.files.values():
                f.close()
