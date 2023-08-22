from collections import OrderedDict
from io import StringIO

from pyxcp.config import readConfiguration

JSON = """{
    "PORT": "COM10",
    "BITRATE": 38400,
    "BYTESIZE": 8,
    "PARITY": "N",
    "STOPBITS": 1,
    "CREATE_DAQ_TIMESTAMPS": false
}"""

TOML = """PORT = "COM10"
BITRATE = 38400
PARITY = "N"
BYTESIZE = 8
STOPBITS = 1
CREATE_DAQ_TIMESTAMPS = false
"""

CONF_JSON = StringIO(JSON)
CONF_JSON.name = "hello.json"

CONF_TOML = StringIO(TOML)
CONF_TOML.name = "hello.toml"


def test_read_empty_config():
    assert readConfiguration(None) == {}
    assert readConfiguration({}) == {}


def test_read_json_config():
    assert readConfiguration(CONF_JSON) == {
        "BITRATE": 38400,
        "BYTESIZE": 8,
        "CREATE_DAQ_TIMESTAMPS": False,
        "PARITY": "N",
        "PORT": "COM10",
        "STOPBITS": 1,
    }


def test_read_toml_config():
    assert readConfiguration(CONF_TOML) == {
        "BITRATE": 38400,
        "BYTESIZE": 8,
        "CREATE_DAQ_TIMESTAMPS": False,
        "PARITY": "N",
        "PORT": "COM10",
        "STOPBITS": 1,
    }


def test_read_dict():
    assert readConfiguration({"A": 1, "B": 2, "C": 3}) == {"A": 1, "B": 2, "C": 3}
    assert readConfiguration(OrderedDict({"A": 1, "B": 2, "C": 3})) == {
        "A": 1,
        "B": 2,
        "C": 3,
    }
