# -*- coding: utf-8 -*-

import argparse
import logging
from array import array
from dataclasses import dataclass, field
from pathlib import Path

# from pprint import pprint
from typing import Any, List

import pyarrow as pa

# import pyarrow.compute as pc
import pyarrow.parquet as pq

from pyxcp.recorder import XcpLogFileUnfolder


MAP_TO_ARROW = {
    "U8": pa.uint8(),
    "I8": pa.int8(),
    "U16": pa.uint16(),
    "I16": pa.int16(),
    "U32": pa.uint32(),
    "I32": pa.int32(),
    "U64": pa.uint64(),
    "I64": pa.int64(),
    "F32": pa.float32(),
    "F64": pa.float64(),
    "F16": pa.float16(),
    # "BF16"
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
# logger.setLevel(logging.INFO)


# sys.argv.append(r"C:\Users\Chris\PycharmProjects\pyxcp\pyxcp\examples\run_daq.xmraw")

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
    arr: List[Storage] = field(default_factory=[])
    #ts0: array[float] = field(default_factory=lambda: array("d"))
    #ts1: array[float] = field(default_factory=lambda: array("d"))
    ts0: List[float] = field(default_factory=lambda: array("Q"))
    ts1: List[float] = field(default_factory=lambda: array("Q"))


class Unfolder(XcpLogFileUnfolder):

    def initialize(self):
        # print("initialize()")
        self.arrow_tables = []
        for dl in self.daq_lists:
            # print("=" * 80)
            # print(dl.name)
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                arrow_type = MAP_TO_ARROW[type_str]
                sd = Storage(name, arrow_type, array(array_txpe))
                print(f"\t{name!r} {array_txpe} {arrow_type}", sd)
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            self.arrow_tables.append(sc)

    def finalize(self) -> Any:
        # print("finalize()")
        result = []
        for arr in self.arrow_tables:
            timestamp0 = arr.ts0
            timestamp1 = arr.ts1
            names = ["timestamp0", "timestamp1"]
            data = [timestamp0, timestamp1

                    ]
            for sd in arr.arr:
                adt = pa.array(sd.arr, type=sd.arrow_type)
                names.append(sd.name)
                data.append(adt)
            table = pa.Table.from_arrays(data, names=names)
            fname = f"{arr.name}.parquet"
            print("Writing table", fname)
            pq.write_table(table, fname)
            print("done.", table.shape)
            result.append(table)
        return result

    def on_daq_list(self, daq_list_num: int, timestamp0: float, timestamp1: float, measurements: list):
        sc = self.arrow_tables[daq_list_num]
        sc.ts0.append(timestamp0)
        sc.ts1.append(timestamp1)
        for idx, elem in enumerate(measurements):
            sto = sc.arr[idx]
            sto.arr.append(elem)


logger.info(f"Processing {args.xmraw_file!r}")
logger.info(f"Processing {Path(args.xmraw_file)!r}")

lfr = Unfolder(args.xmraw_file)
res = lfr.run()
print(res)
