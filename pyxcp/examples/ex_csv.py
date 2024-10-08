import argparse
import logging
import os
import csv
from array import array
from dataclasses import dataclass, field
from mmap import PAGESIZE
from pathlib import Path
from typing import Any, List

from pyxcp.recorder import XcpLogFileDecoder
from pyxcp.recorder.converter import MAP_TO_ARRAY


MAP_TO_SQL = {
    "U8": "INTEGER",
    "I8": "INTEGER",
    "U16": "INTEGER",
    "I16": "INTEGER",
    "U32": "INTEGER",
    "I32": "INTEGER",
    "U64": "INTEGER",
    "I64": "INTEGER",
    "F32": "FLOAT",
    "F64": "FLOAT",
    "F16": "FLOAT",
    "BF16": "FLOAT",
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
    arr: List[Storage] = field(default_factory=[])
    ts0: List[int] = field(default_factory=lambda: array("Q"))
    ts1: List[int] = field(default_factory=lambda: array("Q"))


class Decoder(XcpLogFileDecoder):

    def __init__(self, recording_file_name: str):
        super().__init__(recording_file_name)

    def initialize(self) -> None:
        self.arrow_tables = []
        self.csv_writers = []
        for dl in self.daq_lists:
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                sql_type = MAP_TO_SQL[type_str]
                sd = Storage(name, sql_type, array(array_txpe))
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            writer = csv.writer(open(f"{sc.name}.csv", "w", newline=""), dialect="excel")
            headers = ["ts0", "ts1"] + [e.name for e in sc.arr]
            writer.writerow(headers)
            self.csv_writers.append(writer)
            self.arrow_tables.append(sc)
        print("\nInserting data...")

    def finalize(self) -> None:
        print("Done.")

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        sc = self.arrow_tables[daq_list_num]
        writer = self.csv_writers[daq_list_num]
        data = [timestamp0, timestamp1, *measurements]
        writer.writerow(data)

decoder = Decoder(args.xmraw_file)
decoder.run()
