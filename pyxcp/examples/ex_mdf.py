import argparse
import logging
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import numpy as np
from asammdf import MDF, Signal
from asammdf.blocks.v4_blocks import HeaderBlock  # ChannelGroup
from asammdf.blocks.v4_constants import FLAG_HD_TIME_OFFSET_VALID  # FLAG_HD_LOCAL_TIME,

from pyxcp.recorder import XcpLogFileDecoder


MAP_TO_NP = {
    "U8": np.uint8,
    "I8": np.int8,
    "U16": np.uint16,
    "I16": np.int16,
    "U32": np.uint32,
    "I32": np.int32,
    "U64": np.uint64,
    "I64": np.int64,
    "F32": np.float32,
    "F64": np.float64,
    "F16": np.float16,
    "BF16": np.float16,
}

MAP_TO_ARRAY = {
    "U8": "B",
    "I8": "b",
    "U16": "H",
    "I16": "h",
    "U32": "L",
    "I32": "l",
    "U64": "Q",
    "I64": "q",
    "F32": "f",
    "F64": "d",
    "F16": "f",
    # "BF16"
}

logger = logging.getLogger("PyXCP")

parser = argparse.ArgumentParser(description="Use .xmraw files in an Apache Arrow application.")
parser.add_argument("xmraw_file", help=".xmraw file")
args = parser.parse_args()


@dataclass
class Storage:
    name: str
    arrow_type: Any
    arr: array


@dataclass
class StorageContainer:
    name: str
    arr: list[Storage] = field(default_factory=[])
    ts0: List[int] = field(default_factory=lambda: array("Q"))
    ts1: List[int] = field(default_factory=lambda: array("Q"))


class Decoder(XcpLogFileDecoder):

    def __init__(self, recording_file_name: str):
        super().__init__(recording_file_name)
        self.mdf_file_name = Path(recording_file_name).with_suffix(".mf4")

    def initialize(self) -> None:
        self.tables = []
        for dl in self.daq_lists:
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                arrow_type = MAP_TO_NP[type_str]
                sd = Storage(name, arrow_type, array(array_txpe))
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            self.tables.append(sc)
        print("Extracting DAQ lists...")

    def finalize(self) -> None:
        print("Creating MDF result...")
        timestamp_info = self.parameters.timestamp_info
        hdr = HeaderBlock(
            abs_time=timestamp_info.timestamp_ns,
            tz_offset=timestamp_info.utc_offset,
            daylight_save_time=timestamp_info.dst_offset,
            time_flags=FLAG_HD_TIME_OFFSET_VALID,
        )
        hdr.comment = f"""<HDcomment><TX>Timezone: {timestamp_info.timezone}</TX></HDcomment>"""  # Test-Comment.
        mdf4 = MDF(version="4.10")
        mdf4.header = hdr
        # result = []
        for idx, arr in enumerate(self.tables):
            signals = []
            timestamps = arr.ts0
            for sd in arr.arr:

                signal = Signal(samples=sd.arr, name=sd.name, timestamps=timestamps)
                signals.append(signal)
            print(f"Appending data-group {arr.name!r}")
            mdf4.append(signals, acq_name=arr.name, comment="Created by pyXCP recorder")
        print(f"Writing '{self.mdf_file_name!s}'")
        mdf4.save(self.mdf_file_name, compression=2, overwrite=True)
        print("Done.")
        return mdf4

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        sc = self.tables[daq_list_num]
        sc.ts0.append(timestamp0)
        sc.ts1.append(timestamp1)
        for idx, elem in enumerate(measurements):
            sto = sc.arr[idx]
            sto.arr.append(elem)


decoder = Decoder(args.xmraw_file)
res = decoder.run()
