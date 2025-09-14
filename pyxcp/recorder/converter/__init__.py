"""Convert pyXCPs .xmraw files to common data formats."""

import csv
import logging
import os
import sqlite3
from array import array
from dataclasses import dataclass, field
from mmap import PAGESIZE
from pathlib import Path
from typing import Any, List

import numpy as np
from rich.logging import RichHandler


try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    has_arrow = True
except ImportError:
    has_arrow = False

try:
    import h5py

    has_h5py = True
except ImportError:
    has_h5py = False

try:
    from asammdf import MDF, Signal
    from asammdf.blocks.v4_blocks import HeaderBlock
    from asammdf.blocks.v4_constants import FLAG_HD_TIME_OFFSET_VALID

    has_asammdf = True
except ImportError:
    has_asammdf = False

try:
    import xlsxwriter

    has_xlsxwriter = True

except ImportError:
    has_xlsxwriter = False

from pyxcp import console
from pyxcp.recorder.rekorder import XcpLogFileDecoder as _XcpLogFileDecoder


FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

log = logging.getLogger("rich")

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
    "BF16": "f",
}

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


@dataclass
class Storage:
    name: str
    target_type: Any
    arr: array


@dataclass
class StorageContainer:
    name: str
    arr: List[Storage] = field(default_factory=[])
    timestamp0: List[int] = field(default_factory=lambda: array("Q"))
    timestamp1: List[int] = field(default_factory=lambda: array("Q"))


class XcpLogFileDecoder(_XcpLogFileDecoder):
    """"""

    def __init__(
        self,
        recording_file_name: str,
        out_file_suffix: str,
        remove_file: bool = True,
        target_type_map: dict = None,
        target_file_name: str = "",
    ):
        super().__init__(recording_file_name)
        self.logger = logging.getLogger("PyXCP")
        self.logger.setLevel(logging.DEBUG)
        self.out_file_name = Path(recording_file_name).with_suffix(out_file_suffix)
        self.out_file_suffix = out_file_suffix
        self.target_type_map = target_type_map or {}
        if remove_file:
            try:
                os.unlink(self.out_file_name)
            except FileNotFoundError:
                pass

    def initialize(self) -> None:
        self.on_initialize()

    def on_initialize(self) -> None:
        self.setup_containers()

    def finalize(self) -> None:
        self.on_finalize()

    def on_finalize(self) -> None:
        pass

    def setup_containers(self) -> None:
        self.tables = []
        for dl in self.daq_lists:
            result = []
            for name, type_str in dl.headers:
                array_txpe = MAP_TO_ARRAY[type_str]
                target_type = self.target_type_map.get(type_str)
                sd = Storage(name, target_type, array(array_txpe))
                result.append(sd)
            sc = StorageContainer(dl.name, result)
            self.tables.append(sc)
            self.on_container(sc)

    def on_container(self, sc: StorageContainer) -> None:
        pass


class CollectRows:

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        storage_container = self.tables[daq_list_num]
        storage_container.timestamp0.append(timestamp0)
        storage_container.timestamp1.append(timestamp1)
        for idx, elem in enumerate(measurements):
            storage = storage_container.arr[idx]
            storage.arr.append(elem)


class ArrowConverter(CollectRows, XcpLogFileDecoder):
    """"""

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
        "BF16": pa.float16(),
    }

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(
            recording_file_name=recording_file_name,
            out_file_suffix=".parquet",
            remove_file=False,
            target_type_map=self.MAP_TO_ARROW,
            target_file_name=target_file_name,
        )

    def on_initialize(self) -> None:
        super().on_initialize()

    def on_finalize(self) -> None:
        result = []
        for arr in self.tables:
            timestamp0 = arr.timestamp0
            timestamp1 = arr.timestamp1
            names = ["timestamp0", "timestamp1"]
            data = [timestamp0, timestamp1]
            for sd in arr.arr:
                adt = pa.array(sd.arr, type=sd.target_type)
                names.append(sd.name)
                data.append(adt)
            table = pa.Table.from_arrays(data, names=names)
            fname = f"{arr.name}{self.out_file_suffix}"
            self.logger.info(f"Writing file {fname!r}")
            pq.write_table(table, fname)
            result.append(table)
        return result


class CsvConverter(XcpLogFileDecoder):

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(
            recording_file_name=recording_file_name, out_file_suffix=".csv", remove_file=False, target_file_name=target_file_name
        )

    def on_initialize(self) -> None:
        self.csv_writers = []
        super().on_initialize()

    def on_container(self, sc: StorageContainer) -> None:
        fname = f"{sc.name}{self.out_file_suffix}"
        self.logger.info(f"Creating file {fname!r}.")
        writer = csv.writer(open(fname, "w", newline=""), dialect="excel")
        headers = ["timestamp0", "timestamp1"] + [e.name for e in sc.arr]
        writer.writerow(headers)
        self.csv_writers.append(writer)

    def on_finalize(self) -> None:
        self.logger.info("Done.")

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        writer = self.csv_writers[daq_list_num]
        data = [timestamp0, timestamp1, *measurements]
        writer.writerow(data)


class ExcelConverter(XcpLogFileDecoder):

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(recording_file_name=recording_file_name, out_file_suffix=".xlsx", target_file_name=target_file_name)

    def on_initialize(self) -> None:
        self.logger.info(f"Creating file {str(self.out_file_name)!r}.")
        self.xls_workbook = xlsxwriter.Workbook(self.out_file_name)
        self.xls_sheets = []
        self.rows = []
        super().on_initialize()

    def on_container(self, sc: StorageContainer) -> None:
        sheet = self.xls_workbook.add_worksheet(sc.name)
        self.xls_sheets.append(sheet)
        headers = ["timestamp0", "timestamp1"] + [e.name for e in sc.arr]
        sheet.write_row(0, 0, headers)
        self.rows.append(1)

    def on_finalize(self) -> None:
        self.xls_workbook.close()
        self.logger.info("Done.")

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        sheet = self.xls_sheets[daq_list_num]
        row = self.rows[daq_list_num]
        data = [timestamp0, timestamp1] + measurements
        sheet.write_row(row, 0, data)
        self.rows[daq_list_num] += 1


class HdfConverter(CollectRows, XcpLogFileDecoder):

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(recording_file_name=recording_file_name, out_file_suffix=".h5", target_file_name=target_file_name)

    def on_initialize(self) -> None:
        self.logger.info(f"Creating file {str(self.out_file_name)!r}")
        self.out_file = h5py.File(self.out_file_name, "w")
        super().on_initialize()

    def on_finalize(self) -> None:
        for arr in self.tables:
            timestamp0 = arr.timestamp0
            timestamp1 = arr.timestamp1
            self.out_file[f"/{arr.name}/timestamp0"] = timestamp0
            self.out_file[f"/{arr.name}/timestamp1"] = timestamp1
            for sd in arr.arr:
                self.out_file[f"/{arr.name}/{sd.name}"] = sd.arr
            self.logger.info(f"Writing table {arr.name!r}")
            self.logger.info("Done.")
        self.out_file.close()


class MdfConverter(CollectRows, XcpLogFileDecoder):

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(
            recording_file_name=recording_file_name,
            out_file_suffix=".mf4",
            target_type_map=MAP_TO_NP,
            target_file_name=target_file_name,
        )

    def on_initialize(self) -> None:
        super().on_initialize()

    def on_finalize(self) -> None:
        timestamp_info = self.parameters.timestamp_info
        hdr = HeaderBlock(
            abs_time=timestamp_info.timestamp_ns,
            tz_offset=timestamp_info.utc_offset,
            daylight_save_time=timestamp_info.dst_offset,
            time_flags=FLAG_HD_TIME_OFFSET_VALID,
        )
        hdr.comment = f"""<HDcomment><TX>Timezone: {timestamp_info.timezone}</TX></HDcomment>"""  # Test-Comment.
        mdf4 = MDF(version="4.10", header=hdr)
        for idx, arr in enumerate(self.tables):
            signals = []
            timestamps = arr.timestamp0
            for sd in arr.arr:
                signal = Signal(samples=sd.arr, name=sd.name, timestamps=timestamps)
                signals.append(signal)
            self.logger.info(f"Appending data-group {arr.name!r}")
            mdf4.append(signals, acq_name=arr.name, comment="Created by pyXCP recorder")
        self.logger.info(f"Writing {str(self.out_file_name)!r}")
        mdf4.save(self.out_file_name, compression=2, overwrite=True)
        self.logger.info("Done.")


class SqliteConverter(XcpLogFileDecoder):
    """ """

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

    def __init__(self, recording_file_name: str, target_file_name: str = ""):
        super().__init__(
            recording_file_name=recording_file_name,
            out_file_suffix=".sq3",
            target_type_map=self.MAP_TO_SQL,
            target_file_name=target_file_name,
        )

    def on_initialize(self) -> None:
        self.logger.info(f"Creating database {str(self.out_file_name)!r}.")
        self.create_database(self.out_file_name)
        self.insert_stmt = {}
        super().on_initialize()

    def on_container(self, sc: StorageContainer) -> None:
        self.create_table(sc)
        self.logger.info(f"Creating table {sc.name!r}.")
        self.insert_stmt[sc.name] = (
            f"""INSERT INTO {sc.name}({', '.join(['timestamp0', 'timestamp1'] + [r.name for r in sc.arr])})"""
            f""" VALUES({', '.join(["?" for _ in range(len(sc.arr) + 2)])})"""
        )

    def on_finalize(self) -> None:
        self.conn.commit()
        self.conn.close()
        print("Done.")

    def on_daq_list(self, daq_list_num: int, timestamp0: int, timestamp1: int, measurements: list) -> None:
        sc = self.tables[daq_list_num]
        insert_stmt = self.insert_stmt[sc.name]
        data = [timestamp0, timestamp1, *measurements]
        self.execute(insert_stmt, data)

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
        columns = ["timestamp0 INTEGER", "timestamp1 INTEGER"]
        for elem in sc.arr:
            columns.append(f"{elem.name} {elem.target_type}")
        ddl = f"CREATE TABLE {sc.name}({', '.join(columns)})"
        self.execute(ddl)
        self.execute("INSERT INTO table_names VALUES(?)", [sc.name])

    def execute(self, *args: List[str]) -> None:
        try:
            self.cursor.execute(*args)
        except Exception as e:
            print(e)


CONVERTERS = {
    "arrow": ArrowConverter,
    "csv": CsvConverter,
    "excel": ExcelConverter,
    "hdf5": HdfConverter,
    "mdf": MdfConverter,
    "sqlite3": SqliteConverter,
}

CONVERTER_REQUIREMENTS = {
    "arrow": (has_arrow, "pyarrow"),
    "csv": (True, "csv"),
    "excel": (has_xlsxwriter, "xlsxwriter"),
    "hdf5": (has_h5py, "h5py"),
    "mdf": (has_asammdf, "asammdf"),
    "sqlite3": (True, "csv"),
}


def convert_xmraw(converter_name: str, recording_file_name: str, target_file_name: str, *args, **kwargs) -> None:
    converter_class = CONVERTERS.get(converter_name.lower())
    if converter_class is None:
        console.print(f"Invalid converter name: {converter_name!r}")
        return
    available, pck_name = CONVERTER_REQUIREMENTS.get(converter_name.lower(), (True, ""))
    if not available:
        console.print(f"Converter {converter_name!r} requires package {pck_name!r}.")
        console.print(f"Please run [green]pip install {pck_name}[/green] to install it.")
        return
    # Path(*p.parts[:-1], p.stem)
    converter = converter_class(recording_file_name)
    converter.run()
