#!/usr/bin/env python

import datetime
from pathlib import Path
from typing import List, Dict

import h5py
import numpy as np
from pyxcp.daq_stim import DaqOnlinePolicy, DaqList
from pyxcp import __version__ as pyxcp_version

BATCH_SIZE = 4096

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

MAP_TO_ASAM_HO = {
    "U8": "A_UINT8",
    "I8": "A_INT8",
    "U16": "A_UINT16",
    "I16": "A_INT16",
    "U32": "A_UINT32",
    "I32": "A_INT32",
    "U64": "A_UINT64",
    "I64": "A_INT64",
    "F32": "A_FLOAT32",
    "F64": "A_FLOAT64",
    "F16": "A_FLOAT16",
    "BF16": "A_FLOAT16",
}


class BufferedDataset:
    def __init__(self, dataset: h5py.Dataset):
        self.dataset = dataset
        self.buffer: List[int | float] = []

    def add_sample(self, sample: int | float):
        self.buffer.append(sample)
        if len(self.buffer) >= BATCH_SIZE:
            self.flush()

    def flush(self):
        batch = np.array(self.buffer)
        self.dataset.resize((self.dataset.shape[0] + len(batch),))
        self.dataset[-len(batch) :] = batch
        self.buffer.clear()
        self.dataset.flush()

    def __len__(self):
        return len(self.buffer)


class DatasetGroup:
    def __init__(
        self,
        ts0_ds: BufferedDataset,
        ts1_ds: BufferedDataset,
        datasets: List[BufferedDataset],
    ):
        self.ts0_ds = ts0_ds
        self.ts1_ds = ts1_ds
        self.datasets = datasets

    def feed(self, ts0: int, ts1: int, *datasets):
        self.ts0_ds.add_sample(ts0)
        self.ts1_ds.add_sample(ts1)
        for dataset, value in zip(self.datasets, datasets):
            dataset.add_sample(value)

    def finalize(self):
        for dataset in self.datasets:
            dataset.flush()
        self.ts0_ds.flush()
        self.ts1_ds.flush()


def create_timestamp_column(hdf_file: h5py.File, group_name: str, num: int) -> h5py.Dataset:
    result = hdf_file.create_dataset(
        f"/{group_name}/timestamp{num}",
        shape=(0,),
        maxshape=(None,),
        dtype=np.uint64,
        chunks=True,
    )
    result.attrs["asam_data_type"] = "A_UINT64"
    result.attrs["resolution"] = ("1 nanosecond",)
    return result


class Hdf5OnlinePolicy(DaqOnlinePolicy):
    def __init__(self, file_name: str | Path, daq_lists: List[DaqList], **metadata):
        super().__init__(daq_lists=daq_lists)
        path = Path(file_name)
        if path.suffix != ".h5":
            path = path.with_suffix(".h5")
        self.hdf = h5py.File(path, "w", libver="latest")
        self.metadata = self.set_metadata(**metadata)

    def set_metadata(self, **metadata):
        basic = {
            "tool_name": "pyXCP",
            "tool_version": f"{pyxcp_version}",
            "created": f"{datetime.datetime.now().astimezone().isoformat()}",
        }
        for k, v in (basic | metadata).items():
            self.hdf.attrs[k] = v

    def initialize(self):
        self.log.debug("Hdf5OnlinePolicy::Initialize()")
        self.datasets: Dict[int, DatasetGroup] = {}
        for num, daq_list in enumerate(self.daq_lists):
            if daq_list.stim:
                continue
            grp = self.hdf.create_group(daq_list.name)
            grp.attrs["event_num"] = daq_list.event_num
            grp.attrs["enable_timestamps"] = daq_list.enable_timestamps
            grp.attrs["prescaler"] = daq_list.prescaler
            grp.attrs["priority"] = daq_list.priority
            grp.attrs["direction"] = "STIM" if daq_list.stim else "DAQ"
            ts0 = BufferedDataset(create_timestamp_column(self.hdf, daq_list.name, 0))
            ts1 = BufferedDataset(create_timestamp_column(self.hdf, daq_list.name, 1))
            meas_map = {m.name: m for m in self.daq_lists[num].measurements}
            dsets = []
            for name, _ in daq_list.headers:
                meas = meas_map[name]
                dataset = self.hdf.create_dataset(
                    f"/{daq_list.name}/{meas.name}/raw",
                    shape=(0,),
                    maxshape=(None,),
                    dtype=MAP_TO_NP[meas.data_type],
                    chunks=(1024,),
                )
                sub_group = dataset.parent
                sub_group.attrs["asam_data_type"] = MAP_TO_ASAM_HO.get(meas.data_type, "n/a")
                dataset.attrs["ecu_address"] = meas.address
                dataset.attrs["ecu_address_extension"] = meas.ext
                dsets.append(BufferedDataset(dataset))
            self.datasets[num] = DatasetGroup(ts0_ds=ts0, ts1_ds=ts1, datasets=dsets)
        self.hdf.flush()

    def finalize(self):
        self.log.debug("Hdf5OnlinePolicy::finalize()")
        if hasattr(self, "datasets"):
            for group in self.datasets.values():
                group.finalize()
        if hasattr(self, "hdf"):
            self.hdf.close()

    def on_daq_list(self, daq_list: int, timestamp0: int, timestamp1: int, payload: list):
        group = self.datasets.get(daq_list)
        if group is None:
            self.log.warning(f"Received data for unknown DAQ list {daq_list}")
            return
        group.feed(timestamp0, timestamp1, *payload)
