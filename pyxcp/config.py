#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import pathlib

try:
    import toml
except ImportError:
    HAS_TOML = False
else:
    HAS_TOML = True


def readConfiguration(conf):
    """Read a configuration file either in JSON or TOML format."""
    if conf:
        if isinstance(conf, dict):
            return dict(conf)
        pth = pathlib.Path(conf.name)
        suffix = pth.suffix.lower()
        if suffix == ".json":
            reader = json
        elif suffix == ".toml" and HAS_TOML:
            reader = toml
        else:
            reader = None
        if reader:
            return reader.loads(conf.read())
        else:
            return {}
    else:
        return {}


class Configuration:
    """"""

    def __init__(self, parameters, config):
        self.parameters = parameters
        self.config = config
        for key, (tp, required, default) in self.parameters.items():
            if key in self.config:
                if not isinstance(self.config[key], tp):
                    raise TypeError(f"Parameter {key} requires {tp}")
            else:
                if required:
                    raise AttributeError(f"{key} must be specified in config!")
                else:
                    self.config[key] = default

    def get(self, key):
        return self.config.get(key)

    def __repr__(self):
        return f"{self.config:s}"

    __str__ = __repr__
