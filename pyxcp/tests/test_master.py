#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import mock

from pyxcp.master import Master
from pyxcp import transport


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
    def testGetID(self, Eth):
        tr = Eth()
        tr.request.return_value = bytes(
            [0x00, 0x01, 0xff, 0x06, 0x00, 0x00, 0x00])
        with Master(tr) as xm:
            gid = xm.getID(0x01)
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
        mock_socket.return_value.recv.side_effect = [
            [0x08, 0x00, 0x00, 0x00],
            [0xff, 0x1d, 0xc0, 0xff, 0xdc, 0x05, 0x01, 0x01]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
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

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x02, 0x00, 0x00, 0x00, 0xff, 0x00]))

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDisconnect2(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x01, 0x00, 0x00, 0x00], [0xff]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.disconnect()

        assert res == b''

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfe]))

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetStatus2(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x06, 0x00, 0x00, 0x00],
            [0xff, 0x09, 0x1d, 0x00, 0x34, 0x12]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getStatus()

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

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfd]))

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testSynch(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x02, 0x00, 0x00, 0x00],
            [0xfe, 0x00]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.synch()

        assert res == b'\x00'

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfc]))

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetCommModeInfo2(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x08, 0x00, 0x00, 0x00],
            [0xff, 0x00, 0x01, 0xff, 0x02, 0x00, 0x00, 0x19]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getCommModeInfo()

        assert res.commModeOptional.interleavedMode is False
        assert res.commModeOptional.masterBlockMode is True
        assert res.maxbs == 2
        assert res.minSt == 0
        assert res.queueSize == 0
        assert res.xcpDriverVersionNumber == 25

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x01, 0x00, 0x00, 0x00, 0xfb]))

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetID2(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x08, 0x00, 0x00, 0x00],
            [0xff, 0x00, 0x01, 0xff, 0x06, 0x00, 0x00, 0x00],
            [0x07, 0x00, 0x01, 0x00],
            [0xff, 0x58, 0x43, 0x50, 0x73, 0x69, 0x6d]]
        mock_selector.return_value.select.side_effect = [
            [(0, 1)], [(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            gid = xm.getID(0x01)

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
        mock_socket.return_value.recv.side_effect = [
            [0x01, 0x00, 0x00, 0x00],
            [0xff]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.setRequest(0x15, 0x1234)

            mock_socket.return_value.send.assert_called_with(bytes(
                [0x04, 0x00, 0x00, 0x00, 0xf9, 0x15, 0x12, 0x34]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testGetSeed(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x06, 0x00, 0x00, 0x00],
            [0xff, 0x04, 0x12, 0x34, 0x56, 0x78]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.getSeed(0x00, 0x00)

            mock_socket.return_value.send.assert_called_with(bytes(
                [0x03, 0x00, 0x00, 0x00, 0xf8, 0x00, 0x00]))

        assert res[0] == 4
        assert res[1] == b'\x12\x34\x56\x78'

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testUnlock(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x02, 0x00, 0x00, 0x00],
            [0xff, 0x10]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

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
        mock_socket.return_value.recv.side_effect = [
            [0x01, 0x00, 0x00, 0x00],
            [0xff]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            res = xm.setMta(0x12345678, 0x55)

            mock_socket.return_value.send.assert_called_with(bytes([
                0x08, 0x00, 0x00, 0x00,
                0xf6, 0x00, 0x00, 0x55, 0x78, 0x56, 0x34, 0x12]))

        assert res == b''

    @mock.patch('pyxcp.transport.eth.socket.socket')
    @mock.patch('pyxcp.transport.eth.selectors.DefaultSelector')
    def testDownloadMax(self, mock_selector, mock_socket):
        mock_socket.return_value.recv.side_effect = [
            [0x01, 0x00, 0x00, 0x00], [0xff]]
        mock_selector.return_value.select.side_effect = [[(0, 1)]]

        with Master(transport.Eth('localhost', loglevel="DEBUG")) as xm:
            data = [0xCA, 0xFE, 0xBA, 0xBE]
            xm.downloadMax(*data)

        mock_socket.return_value.send.assert_called_with(bytes(
            [0x05, 0x00, 0x00, 0x00, 0xee, 0xca, 0xfe, 0xba, 0xbe]))
