#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import mock

import time

from pyxcp.master import Master
from pyxcp import transport


class MockSocket:
    def __init__(self):
        self.data = []

    def push(self, data):
        self.data.extend(data)

    def recv(self, bufsize):
        r = self.data[:bufsize]
        self.data = self.data[bufsize:]
        return r

    def select(self, timeout):
        if self.data:
            return [(0, 1)]
        else:
            time.sleep(timeout)
            return []


class TestMaster:

    @mock.patch("pyxcp.transport.Eth")
    def testConnect(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes(
            [0x1d, 0xc0, 0xff, 0xdc, 0x05, 0x01, 0x01])
        with Master(tr) as xm:
            res = xm.connect()
        assert res.maxCto == 255
        assert res.maxDto == 1500
        assert res.protocolLayerVersion == 1
        assert res.transportLayerVersion == 1
        assert res.resource.pgm is True
        assert res.resource.stim is True
        assert res.resource.daq is True
        assert res.resource.calpag is True
        assert res.commModeBasic.optional is True
        assert res.commModeBasic.slaveBlockMode is True
        assert res.commModeBasic.addressGranularity == 'BYTE'
        assert res.commModeBasic.byteOrder == 'INTEL'
        assert xm.maxCto == res.maxCto
        assert xm.maxDto == res.maxDto

    @mock.patch("pyxcp.transport.Eth")
    def testDisconnect(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([])
        with Master(tr) as xm:
            res = xm.disconnect()
        assert res == b''

    @mock.patch("pyxcp.transport.Eth")
    def testGetStatus(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([0x00, 0x1d, 0xff, 0x00, 0x00])
        with Master(tr) as xm:
            res = xm.getStatus()
        assert res.sessionConfiguration == 0
        assert res.sessionStatus.resume is False
        assert res.sessionStatus.daqRunning is False
        assert res.sessionStatus.clearDaqRequest is False
        assert res.sessionStatus.storeDaqRequest is False
        assert res.sessionStatus.storeCalRequest is False
        assert res.resourceProtectionStatus.pgm is True
        assert res.resourceProtectionStatus.stim is True
        assert res.resourceProtectionStatus.daq is True
        assert res.resourceProtectionStatus.calpag is True

    @mock.patch("pyxcp.transport.Eth")
    def testSync(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes([0x00])
        with Master(tr) as xm:
            res = xm.synch()
        assert len(res) == 1

    @mock.patch("pyxcp.transport.Eth")
    def testGetCommModeInfo(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes(
            [0x00, 0x01, 0xff, 0x02, 0x00, 0x00, 0x19])
        with Master(tr) as xm:
            res = xm.getCommModeInfo()
        assert res.commModeOptional.interleavedMode is False
        assert res.commModeOptional.masterBlockMode is True
        assert res.maxbs == 2
        assert res.minSt == 0
        assert res.queueSize == 0
        assert res.xcpDriverVersionNumber == 25

    @mock.patch("pyxcp.transport.Eth")
    def testGetId(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes(
            [0x00, 0x01, 0xff, 0x06, 0x00, 0x00, 0x00])
        with Master(tr) as xm:
            gid = xm.getId(0x01)
            tr.request.return_value = bytes(
                [0x58, 0x43, 0x50, 0x73, 0x69, 0x6d])
            res = xm.upload(gid.length)
        assert gid.mode == 0
        assert gid.reserved == 65281
        assert gid.length == 6
        assert res == b'XCPsim'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testConnect2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x08, 0x00, 0x00, 0x00,
            0xff, 0x1d, 0xc0, 0xff, 0xdc, 0x05, 0x01, 0x01])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.connect()

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x02, 0x00, 0x00, 0x00, 0xff, 0x00]))

        assert res.maxCto == 255
        assert res.maxDto == 1500
        assert res.protocolLayerVersion == 1
        assert res.transportLayerVersion == 1
        assert res.resource.pgm is True
        assert res.resource.stim is True
        assert res.resource.daq is True
        assert res.resource.calpag is True
        assert res.commModeBasic.optional is True
        assert res.commModeBasic.slaveBlockMode is True
        assert res.commModeBasic.addressGranularity == 'BYTE'
        assert res.commModeBasic.byteOrder == 'INTEL'
        assert xm.maxCto == res.maxCto
        assert xm.maxDto == res.maxDto

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDisconnect2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.disconnect()

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfe]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetStatus2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x06, 0x00, 0x00, 0x00, 0xff, 0x09, 0x1d, 0x00, 0x34, 0x12])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getStatus()

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfd]))

        assert res.sessionStatus.storeCalRequest is True
        assert res.sessionStatus.storeDaqRequest is False
        assert res.sessionStatus.clearDaqRequest is True
        assert res.sessionStatus.daqRunning is False
        assert res.sessionStatus.resume is False
        assert res.resourceProtectionStatus.pgm is True
        assert res.resourceProtectionStatus.stim is True
        assert res.resourceProtectionStatus.daq is True
        assert res.resourceProtectionStatus.calpag is True
        assert res.sessionConfiguration == 0x1234

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testSynch(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x02, 0x00, 0x00, 0x00, 0xfe, 0x00])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.synch()

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfc]))

        assert res == b'\x00'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetCommModeInfo2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x08, 0x00, 0x00, 0x00,
            0xff, 0x00, 0x01, 0xff, 0x02, 0x00, 0x00, 0x19])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getCommModeInfo()

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfb]))

        assert res.commModeOptional.interleavedMode is False
        assert res.commModeOptional.masterBlockMode is True
        assert res.maxbs == 2
        assert res.minSt == 0
        assert res.queueSize == 0
        assert res.xcpDriverVersionNumber == 25

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetId2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x08, 0x00, 0x00, 0x00,
            0xff, 0x00, 0x01, 0xff, 0x06, 0x00, 0x00, 0x00,
            0x07, 0x00, 0x01, 0x00,
            0xff, 0x58, 0x43, 0x50, 0x73, 0x69, 0x6d])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            gid = xm.getId(0x01)

            mock_socket.return_value.send.assert_called_with(bytes(
                [0x02, 0x00, 0x00, 0x00, 0xfa, 0x01]))

            res = xm.upload(gid.length)

            mock_socket.return_value.send.assert_called_with(bytes(
                [0x02, 0x00, 0x01, 0x00, 0xf5, 0x06]))

        assert gid.mode == 0
        assert gid.reserved == 65281
        assert gid.length == 6
        assert res == b'XCPsim'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testSetRequest(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.setRequest(0x15, 0x1234)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x04, 0x00, 0x00, 0x00, 0xf9, 0x15, 0x12, 0x34]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetSeed(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x06, 0x00, 0x00, 0x00,
            0xff, 0x04, 0x12, 0x34, 0x56, 0x78])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getSeed(0x00, 0x00)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x03, 0x00, 0x00, 0x00, 0xf8, 0x00, 0x00]))

        assert res[0] == 4
        assert res[1] == b'\x12\x34\x56\x78'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testUnlock(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x02, 0x00, 0x00, 0x00,
            0xff, 0x10])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.unlock(0x04, [0x12, 0x34, 0x56, 0x78])

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x06, 0x00, 0x00, 0x00, 0xf7, 0x04, 0x12, 0x34, 0x56, 0x78]))

        assert res.calpag is False
        assert res.daq is False
        assert res.stim is False
        assert res.pgm is True

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testSetMta(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.setMta(0x12345678, 0x55)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x08, 0x00, 0x00, 0x00,
            0xf6, 0x00, 0x00, 0x55, 0x78, 0x56, 0x34, 0x12]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testUpload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x09, 0x00, 0x00, 0x00,
            0xff, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.upload(8)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x02, 0x00, 0x00, 0x00,
            0xf5, 0x08]))

        assert res == b'\x01\x02\x03\x04\x05\x06\x07\x08'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testShortUpload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x09, 0x00, 0x00, 0x00,
            0xff, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.shortUpload(8, 0xcafebabe, 1)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x08, 0x00, 0x00, 0x00,
            0xf4, 0x08, 0x00, 0x01, 0xbe, 0xba, 0xfe, 0xca]))

        assert res == b'\x01\x02\x03\x04\x05\x06\x07\x08'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testBuildChecksum(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x08, 0x00, 0x00, 0x00,
            0xff, 0x09, 0x00, 0x00, 0x04, 0x05, 0x06, 0x07])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.buildChecksum(1024)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x08, 0x00, 0x00, 0x00,
            0xf3, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00]))

        assert res.checksumType == "XCP_CRC_32"
        assert res.checksum == 0x07060504

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testTransportLayerCmd(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x03, 0x00, 0x00, 0x00,
            0xff, 0xaa, 0xbb])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xbe, 0xef]
            res = xm.transportLayerCmd(0x55, *data)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x04, 0x00, 0x00, 0x00,
            0xf2, 0x55, 0xbe, 0xef]))

        assert res == b'\xaa\xbb'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testUserCmd(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([
            0x03, 0x00, 0x00, 0x00,
            0xff, 0xaa, 0xbb])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xbe, 0xef]
            res = xm.userCmd(0x55, *data)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x04, 0x00, 0x00, 0x00,
            0xf1, 0x55, 0xbe, 0xef]))

        assert res == b'\xaa\xbb'

    # todo: GET_VERSION

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDownload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.download(*data)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x06, 0x00, 0x00, 0x00, 0xf0, 0x04, 0xca, 0xfe, 0xba, 0xbe]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDownloadNext(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.downloadNext(*data)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x06, 0x00, 0x00, 0x00, 0xef, 0x04, 0xca, 0xfe, 0xba, 0xbe]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDownloadMax(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.downloadMax(*data)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x05, 0x00, 0x00, 0x00, 0xee, 0xca, 0xfe, 0xba, 0xbe]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testShortDownload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.shortDownload(0x12345678, 0x55, *data)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x0c, 0x00, 0x00, 0x00, 0xed, 0x04, 0x00, 0x55,
            0x78, 0x56, 0x34, 0x12, 0xca, 0xfe, 0xba, 0xbe]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testModifyBits(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.modifyBits(0xff, 0x1234, 0xabcd)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x06, 0x00, 0x00, 0x00, 0xec, 0xff, 0x34, 0x12,
            0xcd, 0xab]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testSetCalPage(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.setCalPage(0x03, 0x12, 0x34)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x04, 0x00, 0x00, 0x00, 0xeb, 0x03, 0x12, 0x34]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetCalPage(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x04, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x55])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getCalPage(0x02, 0x44)

        mock_socket.return_value.send.assert_called_with(bytes([
            0x03, 0x00, 0x00, 0x00, 0xea, 0x02, 0x44]))

        assert res == 0x55

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testPageSwitchingCommands(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        ms.push([0x03, 0x00, 0x00, 0x00, 0xff, 0x10, 0x01])
        ms.push([0x08, 0x00, 0x01, 0x00,
                 0xff, 0x00, 0x00, 0x00, 0x78, 0x56, 0x34, 0x12])
        ms.push([0x03, 0x00, 0x02, 0x00, 0xff, 0x3F, 0x55])
        ms.push([0x01, 0x00, 0x03, 0x00, 0xff])
        ms.push([0x03, 0x00, 0x04, 0x00, 0xff, 0x00, 0x01])
        ms.push([0x01, 0x00, 0x05, 0x00, 0xff])

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getPagProcessorInfo()

            mock_socket.return_value.send.assert_called_with(bytes([
                0x01, 0x00, 0x00, 0x00, 0xe9]))

            assert res.maxSegments == 16
            assert res.pagProperties == 0x01

            res = xm.getSegmentInfo(2, 5, 1, 3)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x05, 0x00, 0x01, 0x00, 0xe8, 0x02, 0x05, 0x01, 0x03]))

            assert res.mappingInfo == 0x12345678

            res = xm.getPageInfo(0x12, 0x34)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x04, 0x00, 0x02, 0x00, 0xe7, 0x00, 0x12, 0x34]))

            assert res[0].xcpWriteAccessWithEcu
            assert res[1] == 0x55

            res = xm.setSegmentMode(0x01, 0x23)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x03, 0x00, 0x03, 0x00, 0xe6, 0x01, 0x23]))

            assert res == b''

            res = xm.getSegmentMode(0x23)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x03, 0x00, 0x04, 0x00, 0xe5, 0x00, 0x23]))

            assert res == 0x01

            res = xm.copyCalPage(0x12, 0x34, 0x56, 0x78)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x05, 0x00, 0x05, 0x00, 0xe4, 0x12, 0x34, 0x56, 0x78]))

            assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDaqCommands(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            ms.push([0x01, 0x00, 0x00, 0x00, 0xff])

            res = xm.setDaqPtr(2, 3, 4)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x06, 0x00, 0x00, 0x00, 0xe2, 0x00, 0x02, 0x00, 0x03, 0x04]))

            assert res == b''

            ms.push([0x01, 0x00, 0x01, 0x00, 0xff])

            res = xm.writeDaq(31, 15, 1, 0x12345678)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x08, 0x00, 0x01, 0x00,
                0xe1, 0x1f, 0x0f, 0x01, 0x78, 0x56, 0x34, 0x12]))

            assert res == b''

            ms.push([0x01, 0x00, 0x02, 0x00, 0xff])

            res = xm.setDaqListMode(0x3b, 256, 512, 1, 0xff)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x08, 0x00, 0x02, 0x00,
                0xe0, 0x3b, 0x00, 0x01, 0x00, 0x02, 0x01, 0xff]))

            assert res == b''

            ms.push([0x01, 0x00, 0x03, 0x00, 0xff])

            res = xm.startStopDaqList(1, 512)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x04, 0x00, 0x03, 0x00, 0xde, 0x01, 0x00, 0x02]))

            assert res == b''

            ms.push([0x01, 0x00, 0x04, 0x00, 0xff])

            res = xm.startStopSynch(3)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x02, 0x00, 0x04, 0x00, 0xdd, 0x03]))

            assert res == b''

            # todo: xm.writeDaqMultiple()
            # todo: xm.setDaqPackedMode()
            # todo: xm.getDaqPackedMode()

            ms.push([0x08, 0x00, 0x05, 0x00,
                     0xff, 0x1f, 0x03, 0x04, 0x78, 0x56, 0x34, 0x12])

            res = xm.readDaq()

            mock_socket.return_value.send.assert_called_with(bytes([
                0x01, 0x00, 0x05, 0x00, 0xdb]))

            assert res.bitOffset == 31
            assert res.sizeofDaqElement == 3
            assert res.adressExtension == 4
            assert res.address == 0x12345678

            ms.push([0x08, 0x00, 0x06, 0x00,
                     0xff, 0x00, 0x03, 0x04, 0x78, 0x56, 0x34, 0x12])

            res = xm.getDaqClock()

            mock_socket.return_value.send.assert_called_with(bytes([
                0x01, 0x00, 0x06, 0x00, 0xdc]))

            # todo: assert res.triggerInfo ==
            # todo: assert res.payloadFmt ==
            # todo: assert res.timestamp == 0x12345678
            assert res == 0x12345678

            ms.push([0x08, 0x00, 0x07, 0x00,
                     0xff, 0x55, 0x00, 0x01, 0x34, 0x12, 0x22, 0x03])

            res = xm.getDaqProcessorInfo()

            mock_socket.return_value.send.assert_called_with(bytes([
                0x01, 0x00, 0x07, 0x00, 0xda]))

            assert res.daqProperties.overloadMsb is True
            assert res.daqProperties.bitStimSupported is False
            assert res.maxDaq == 256
            assert res.maxEventChannel == 0x1234
            assert res.minDaq == 0x22
            assert res.daqKeyByte.Optimisation_Type == "OM_ODT_TYPE_64"

            ms.push([0x08, 0x00, 0x08, 0x00,
                     0xff, 0x12, 0x34, 0x56, 0x78, 0xaa, 0x34, 0x12])

            res = xm.getDaqResolutionInfo()

            mock_socket.return_value.send.assert_called_with(bytes([
                0x01, 0x00, 0x08, 0x00, 0xd9]))

            assert res.granularityOdtEntrySizeDaq == 0x12
            assert res.maxOdtEntrySizeDaq == 0x34
            assert res.granularityOdtEntrySizeStim == 0x56
            assert res.maxOdtEntrySizeStim == 0x78
            assert res.timestampMode.size == "S2"
            assert res.timestampMode.fixed is True
            assert res.timestampMode.unit == "DAQ_TIMESTAMP_UNIT_1PS"
            assert res.timestampTicks == 0x1234

            # todo: xm.getDaqListMode()
            # todo: xm.getDaqEventInfo()
            # todo: xm.dtoCtrProperties()
            # todo: xm.clearDaqList()
            # todo: xm.getDaqListInfo()
            # todo: xm.freeDaq()
            # todo: xm.allocDaq()
            # todo: xm.allocOdt()
            # todo: xm.allocOdtEntry()
