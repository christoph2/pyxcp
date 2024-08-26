import argparse
import logging
import os
import sqlite3
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
        self.sq3_file_name = Path(recording_file_name).with_suffix(".sq3")
        try:
            os.unlink(self.sq3_file_name)
        except Exception as e:
            print(e)

    def initialize(self) -> None:
        self.create_database(self.sq3_file_name)
        self.arrow_tables = []
        self.insert_stmt = {}
        for dl in self.daq_lists:
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                sql_type = MAP_TO_SQL[type_str]
                sd = Storage(name, sql_type, array(array_txpe))
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            print(f"Creating table {sc.name!r}.")
            self.create_table(sc)
            self.insert_stmt[sc.name] = (
                f"""INSERT INTO {sc.name}({', '.join(['ts0', 'ts1'] + [r.name for r in sc.arr])}) VALUES({', '.join(["?" for _ in range(len(sc.arr) + 2)])})"""
            )
            self.arrow_tables.append(sc)
        print("\nInserting data...")

    def create_database(self, db_name: str) -> None:
        self.conn = sqlite3.Connection(db_name)
        self.cursor = self.conn.cursor()
        self.execute("PRAGMA FOREIGN_KEYS=ON")
        self.execute(f"PRAGMA PAGE_SIZE={PAGESIZE}")
        self.execute("PRAGMA SYNCHRONOUS=OFF")
        self.execute("PRAGMA LOCKING_MODE=EXCLUSIVE")
        self.execute("PRAGMA TEMP_STORE=MEMORY")

        timestamp_info = self.parameters.timestamp_info
        self.execute(
            "CREATE TABLE timestamp_info(timestamp_ns INTEGER, utc_offset INTEGER, dst_offset INTEGER, timezone VARCHAR(255))"
        )
        self.execute("CREATE TABLE table_names(name VARCHAR(255))")
        self.execute(
            "INSERT INTO timestamp_info VALUES(?, ?, ?, ?)",
            [timestamp_info.timestamp_ns, timestamp_info.utc_offset, timestamp_info.dst_offset, timestamp_info.timezone],
        )

    def create_table(self, sc: StorageContainer) -> None:
        columns = ["ts0 INTEGER", "ts1 INTEGER"]
        for elem in sc.arr:
            columns.append(f"{elem.name} {elem.arrow_type}")
        ddl = f"CREATE TABLE {sc.name}({', '.join(columns)})"
        self.execute(ddl)
        self.execute("INSERT INTO table_names VALUES(?)", [sc.name])

    def execute(self, *args: List[str]) -> None:
        try:
            self.cursor.execute(*args)
        except Exception as e:
            print(e)

    def finalize(self) -> None:
        self.conn.commit()
        self.conn.close()
        print("Done.")

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        sc = self.arrow_tables[daq_list_num]
        insert_stmt = self.insert_stmt[sc.name]
        data = [timestamp0, timestamp1, *measurements]
        self.execute(insert_stmt, data)


decoder = Decoder(args.xmraw_file)
decoder.run()
