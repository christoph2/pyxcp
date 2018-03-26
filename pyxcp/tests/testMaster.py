#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest import mock

from pyxcp.master import Master
from pyxcp import transport

"""
[in test_my_module]
@patch('external_module.api_call')
def test_some_func(self, mock_api_call):
     mock_api_call.return_value =
MagicMock(status_code=200, response=json.dumps({'key':'value'}))
     my_module.some_func()

##
##
##
m = MagicMock()
m.foo() #no error raised

# Response objects have a status_code attribute
m = MagicMock(spec=Response, status_code=200, response=json.dumps({'key': 'value'}))
m.foo() #raises AttributeError
m.status_code #no error raised
"""

class TestMaster(unittest.TestCase):

    @mock.patch("pyxcp.transport.Eth")
    def testConnect(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([0x1d, 0xc0, 0xff, 0xdc, 0x05, 0x01, 0x01])
        with Master(tr) as xm:
            res = xm.connect()
        self.assertEqual(res.maxCto, 255)
        self.assertEqual(res.maxDto, 1500)
        self.assertEqual(res.protocolLayerVersion, 1)
        self.assertEqual(res.transportLayerVersion, 1)
        self.assertEqual(res.resource.pgm , True)
        self.assertEqual(res.resource.stim , True)
        self.assertEqual(res.resource.daq , True)
        self.assertEqual(res.resource.calpag , True)
        self.assertEqual(res.commModeBasic.optional, True)
        self.assertEqual(res.commModeBasic.slaveBlockMode, True)
        self.assertEqual(res.commModeBasic.addressGranularity, 'BYTE')
        self.assertEqual(res.commModeBasic.byteOrder, 'INTEL')
        self.assertEqual(xm.maxCto, res.maxCto)
        self.assertEqual(xm.maxDto, res.maxDto)

    @mock.patch("pyxcp.transport.Eth")
    def testDisconnect(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([])
        with Master(tr) as xm:
            res = xm.disconnect()
        self.assertEqual(res, None)

    @mock.patch("pyxcp.transport.Eth")
    def testGetStatus(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([0x00, 0x1d, 0xff, 0x00, 0x00])
        with Master(tr) as xm:
            res = xm.getStatus()
        self.assertEqual(res.sessionConfiguration, 0)
        self.assertEqual(res.sessionStatus.resume, False)
        self.assertEqual(res.sessionStatus.daqRunning, False)
        self.assertEqual(res.sessionStatus.clearDaqRequest, False)
        self.assertEqual(res.sessionStatus.storeDaqRequest, False)
        self.assertEqual(res.sessionStatus.storeCalRequest, False)
        self.assertEqual(res.resourceProtectionStatus.pgm, True)
        self.assertEqual(res.resourceProtectionStatus.stim, True)
        self.assertEqual(res.resourceProtectionStatus.daq, True)
        self.assertEqual(res.resourceProtectionStatus.calpag, True)


def main():
    unittest.main()

if __name__ == '__main__':
    main()

