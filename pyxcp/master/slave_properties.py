from dataclasses import dataclass


@dataclass
class SlaveProperties:
    slave_little_endian: bool = False


slaveProperties = SlaveProperties()
