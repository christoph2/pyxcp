import logging
from array import array
from dataclasses import dataclass, field
from typing import Any, List


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

logger = logging.getLogger("PyXCP")


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
