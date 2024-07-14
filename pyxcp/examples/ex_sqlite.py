# -*- coding: utf-8 -*-

import argparse
import logging
import os
import sqlite3
from array import array
from dataclasses import dataclass, field
from mmap import PAGESIZE
from pathlib import Path
from typing import Any, List

from pyxcp.recorder import XcpLogFileUnfolder


# sys.argv.append(r"D:\pyxcp\run_daq.xmraw")

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
    arr: List[Storage] = field(default_factory=[])
    # ts0: array[int] = field(default_factory=lambda: array("d"))
    # ts1: array[int] = field(default_factory=lambda: array("d"))
    ts0: List[int] = field(default_factory=lambda: array("Q"))
    ts1: List[int] = field(default_factory=lambda: array("Q"))


class Unfolder(XcpLogFileUnfolder):

    def __init__(self, recording_file_name: str):
        super().__init__(recording_file_name)
        self.sq3_file_name = Path(recording_file_name).with_suffix(".sq3")
        try:
            os.unlink(self.sq3_file_name)
        except Exception as e:
            print(e)

    def initialize(self):
        # print("initialize()")
        self.create_database(self.sq3_file_name)
        self.arrow_tables = []
        self.insert_stmt = {}
        for dl in self.daq_lists:
            # print("=" * 80)
            # print(dl.name)
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                sql_type = MAP_TO_SQL[type_str]
                sd = Storage(name, sql_type, array(array_txpe))
                print(f"\t{name!r} {array_txpe} {sql_type}", sd)
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            self.create_table(sc)
            self.insert_stmt[sc.name] = (
                f"INSERT INTO {sc.name}({', '.join(['ts0', 'ts1'] + [r.name for r in sc.arr])}) VALUES({', '.join(["?" for _ in range(len(sc.arr) + 2)])})"
            )
            self.arrow_tables.append(sc)

    def create_database(self, db_name: str) -> None:
        self.conn = sqlite3.Connection(db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA FOREIGN_KEYS=ON")
        self.cursor.execute(f"PRAGMA PAGE_SIZE={PAGESIZE}")
        self.cursor.execute("PRAGMA SYNCHRONOUS=OFF")
        self.cursor.execute("PRAGMA LOCKING_MODE=EXCLUSIVE")
        self.cursor.execute("PRAGMA TEMP_STORE=MEMORY")

    def create_table(self, sc: StorageContainer) -> None:
        columns = ["ts0 INTEGER", "ts1 INTEGER"]
        for elem in sc.arr:
            columns.append(f"{elem.name} {elem.arrow_type}")
        ddl = f"CREATE TABLE {sc.name}({', '.join(columns)})"
        print(ddl)
        try:
            self.cursor.execute(ddl)
        except Exception as e:
            print(e)

    def finalize(self) -> Any:
        self.conn.commit()
        self.conn.close()

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list):
        sc = self.arrow_tables[daq_list_num]
        insert_stmt = self.insert_stmt[sc.name]
        data = [timestamp0, timestamp1, *measurements]
        self.cursor.execute(insert_stmt, data)


logger.info(f"Processing {args.xmraw_file!r}")
logger.info(f"Processing {Path(args.xmraw_file)!r}")

lfr = Unfolder(args.xmraw_file)
res = lfr.run()
print(res)
