#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for python-can - github.com/hardbyte/python-can
"""
import pyxcp.transport.can as can
import re
from collections import OrderedDict

from can import Bus
from can import CanError
from can import Message

NUMBER = re.compile(r"(?P<hex>0[x|X])?(?P<number>[0-9]+)", re.VERBOSE)


class PythonCAN:
    """"""

    def __init__(self, bustype):
        self.bustype = bustype
        self.connected = False

    def init(self, parent, receive_callback):
        self.parent = parent
        self.is_fd = self.config.get("FD")

    def connect(self):
        if self.connected:
            return

        self.kwargs = OrderedDict()
        # Fetch driver keyword arguments.
        self._fetch_kwargs(False)
        self._fetch_kwargs(True)
        can_id = self.parent.can_id_master
        can_filter = {
            "can_id": can_id.id,
            "can_mask": can.MAX_29_BIT_IDENTIFIER if can_id.is_extended else can.MAX_11_BIT_IDENTIFIER,
            "extended": can_id.is_extended,
        }
        self.bus = Bus(bustype=self.bustype, **self.kwargs)
        self.bus.set_filters([can_filter])
        self.parent.logger.debug("Python-CAN driver: {} - {}]".format(self.bustype, self.bus))
        self.connected = True

    def _fetch_kwargs(self, local):
        if local:
            base = self
        else:
            base = self.parent
        for param, arg in base.PARAMETER_TO_KW_ARG_MAP.items():
            value = base.config.get(param)
            # if param == "CHANNEL":
            #    value = self._handle_channel(value)
            self.kwargs[arg] = value

    def _handle_channel(self, value):
        match = NUMBER.match(value)
        if match:
            gd = match.groupdict()
            base = 16 if not gd["hex"] is None else 10
            return int(value, base)
        else:
            return value

    def close(self):
        if self.connected:
            self.bus.shutdown()
        self.connected = False

    def transmit(self, payload):
        frame = Message(
            arbitration_id=self.parent.can_id_slave.id,
            is_extended_id=True if self.parent.can_id_slave.is_extended else False,
            is_fd=self.is_fd,
            data=payload,
        )
        self.bus.send(frame)

    def read(self):
        if not self.connected:
            return None
        try:
            frame = self.bus.recv(5)
        except CanError:
            return None
        else:
            if frame is None or frame.arbitration_id != self.parent.can_id_master.id or not len(frame.data):
                return None  # Timeout condition.
            extended = frame.is_extended_id
            identifier = can.Identifier.make_identifier(frame.arbitration_id, extended)
            return can.Frame(
                id_=identifier,
                dlc=frame.dlc,
                data=frame.data,
                timestamp=frame.timestamp,
            )

    def getTimestampResolution(self):
        return 10 * 1000
