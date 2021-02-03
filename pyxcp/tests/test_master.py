#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import deque
from unittest import mock

import time
import struct

from pyxcp.transport.can import CanInterfaceBase

from pyxcp.master import Master
from pyxcp import transport, types


class MockSocket:
    def __init__(self):
        self.data = bytearray()
        self.ctr = 0

    # push frame consisting of header (len + ctr) and packet
    def push_frame(self, frame):
        try:
            self.data.extend(frame)
        except TypeError:
            self.data.extend(bytes.fromhex(frame))
        self.ctr += 1

    # push packet, automatically add header (len + ctr)
    def push_packet(self, data):
        try:
            data = bytes.fromhex(data)
        except TypeError:
            pass

        header = struct.pack("<HH", len(data), self.ctr)
        self.push_frame(header + data)

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

    def connect(self):
        pass


class MockCanInterface(CanInterfaceBase):
    def __init__(self):
        self.data = deque()
        self.receive_callback = None

    def init(self, parent, receive_callback):
        self.receive_callback = receive_callback

    # push packet
    def push_packet(self, data):
        try:
            data = bytes.fromhex(data)
        except TypeError:
            pass
        # no header on CAN
        self.push_frame(data)

    def push_frame(self, packet):
        self.data.append(packet)

    def transmit(self, payload: bytes):
        time.sleep(0.001)
        try:
            resp = self.data.popleft()
            if resp:
                self.receive_callback(resp)
        except IndexError:
            pass

    def close(self):
        pass

    def connect(self):
        pass

    def read(self):
        pass

    def getTimestampResolution(self):
        pass


class TestMaster:

    DefaultConnectCmd = bytes([0x02, 0x00, 0x00, 0x00, 0xFF, 0x00])
    DefaultConnectResponse = "FF 3D C0 FF DC 05 01 01"

    @mock.patch("pyxcp.transport.eth")
    def testConnect(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.request.return_value = bytes([0x1D, 0xC0, 0xFF, 0xDC, 0x05, 0x01, 0x01])

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
        assert res.commModeBasic.addressGranularity == types.AddressGranularity.BYTE
        assert res.commModeBasic.byteOrder == types.ByteOrder.INTEL
        assert xm.slaveProperties.maxCto == res.maxCto
        assert xm.slaveProperties.maxDto == res.maxDto

    @mock.patch("pyxcp.transport.eth")
    def testDisconnect(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.request.return_value = bytes([])
            res = xm.disconnect()
        assert res == b""

    @mock.patch("pyxcp.transport.eth")
    def testGetStatus(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.request.return_value = bytes([0x1D, 0xC0, 0xFF, 0xDC, 0x05, 0x01, 0x01])

            res = xm.connect()

            xm.transport.request.return_value = bytes([0x00, 0x1D, 0xFF, 0x00, 0x00])

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

    @mock.patch("pyxcp.transport.eth")
    def testSync(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.request.return_value = bytes([0x00])
            res = xm.synch()
        assert len(res) == 1

    @mock.patch("pyxcp.transport.eth")
    def testGetCommModeInfo(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.request.return_value = bytes([0x1D, 0xC0, 0xFF, 0xDC, 0x05, 0x01, 0x01])

            res = xm.connect()

            xm.transport.request.return_value = bytes([0x00, 0x01, 0xFF, 0x02, 0x00, 0x00, 0x19])

            res = xm.getCommModeInfo()

        assert res.commModeOptional.interleavedMode is False
        assert res.commModeOptional.masterBlockMode is True
        assert res.maxBs == 2
        assert res.minSt == 0
        assert res.queueSize == 0
        assert res.xcpDriverVersionNumber == 25

    @mock.patch("pyxcp.transport.eth")
    def testGetId(self, eth):
        with Master("eth") as xm:
            xm.transport = eth()
            xm.transport.MAX_DATAGRAM_SIZE = 512
            xm.transport.request.return_value = bytes([0x1D, 0xC0, 0xFF, 0xDC, 0x05, 0x01, 0x01])

            res = xm.connect()

            xm.transport.request.return_value = bytes([0x00, 0x01, 0xFF, 0x06, 0x00, 0x00, 0x00])

            gid = xm.getId(0x01)
            xm.transport.DATAGRAM_SIZE = 512
            xm.transport.request.return_value = bytes([0x58, 0x43, 0x50, 0x73, 0x69, 0x6D])
            res = xm.upload(gid.length)
        assert gid.mode == 0
        assert gid.length == 6
        assert res == b"XCPsim"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testConnect2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            assert res.maxCto == 255
            assert res.maxDto == 1500
            assert res.protocolLayerVersion == 1
            assert res.transportLayerVersion == 1
            assert res.resource.dbg is True
            assert res.resource.pgm is True
            assert res.resource.stim is True
            assert res.resource.daq is True
            assert res.resource.calpag is True
            assert res.commModeBasic.optional is True
            assert res.commModeBasic.slaveBlockMode is True
            assert res.commModeBasic.addressGranularity == types.AddressGranularity.BYTE
            assert res.commModeBasic.byteOrder == types.ByteOrder.INTEL

            assert xm.slaveProperties.byteOrder == res.commModeBasic.byteOrder
            assert xm.slaveProperties.maxCto == res.maxCto
            assert xm.slaveProperties.maxDto == res.maxDto

            ms.push_frame("06 00 01 00 FF 00 01 05 01 04")

            res = xm.getVersion()

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x01, 0x00, 0xC0, 0x00]))

            assert res.protocolMajor == 1
            assert res.protocolMinor == 5
            assert res.transportMajor == 1
            assert res.transportMinor == 4

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testDisconnect2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("01 00 01 00 FF")

            res = xm.disconnect()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x01, 0x00, 0xFE]))

        assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testGetStatus2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 09 1D 00 34 12")

            res = xm.getStatus()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x01, 0x00, 0xFD]))

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

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testSynch(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x02, 0x00, 0x01, 0x00, 0xFE, 0x00])

            res = xm.synch()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x01, 0x00, 0xFC]))

        assert res == b"\x00"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testGetCommModeInfo2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 00 01 FF 02 00 00 19")

            res = xm.getCommModeInfo()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x01, 0x00, 0xFB]))

        assert res.commModeOptional.interleavedMode is False
        assert res.commModeOptional.masterBlockMode is True
        assert res.maxBs == 2
        assert res.minSt == 0
        assert res.queueSize == 0
        assert res.xcpDriverVersionNumber == 25

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testGetId2(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x08, 0x00, 0x01, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00])

            gid = xm.getId(0x01)

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x01, 0x00, 0xFA, 0x01]))

            assert gid.mode == 0
            assert gid.length == 6

            ms.push_frame([0x07, 0x00, 0x02, 0x00, 0xFF, 0x58, 0x43, 0x50, 0x73, 0x69, 0x6D])

            res = xm.upload(gid.length)

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x02, 0x00, 0xF5, 0x06]))

            assert res == b"XCPsim"

            ms.push_frame(
                [
                    0x0E,
                    0x00,
                    0x03,
                    0x00,
                    0xFF,
                    0x01,
                    0x00,
                    0x00,
                    0x06,
                    0x00,
                    0x00,
                    0x00,
                    0x58,
                    0x43,
                    0x50,
                    0x73,
                    0x69,
                    0x6D,
                ]
            )

            gid = xm.getId(0x01)

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x03, 0x00, 0xFA, 0x01]))

            assert gid.mode == 1
            assert gid.length == 6
            assert gid.identification == list(b"XCPsim")

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testSetRequest(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x01, 0x00, 0x01, 0x00, 0xFF])

            res = xm.setRequest(0x15, 0x1234)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x01, 0x00, 0xF9, 0x15, 0x12, 0x34]))

        assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testGetSeed(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 04 12 34 56 78")

            res = xm.getSeed(0x00, 0x00)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x01, 0x00, 0xF8, 0x00, 0x00]))

        assert res.length == 4
        assert res.seed == list(b"\x12\x34\x56\x78")

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testUnlock(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 10")

            res = xm.unlock(0x04, [0x12, 0x34, 0x56, 0x78])

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xF7, 0x04, 0x12, 0x34, 0x56, 0x78])
            )

        assert res.calpag is False
        assert res.daq is False
        assert res.stim is False
        assert res.pgm is True

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testSetMta(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("01 00 01 00 FF")

            res = xm.setMta(0x12345678, 0x55)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x01, 0x00, 0xF6, 0x00, 0x00, 0x55, 0x78, 0x56, 0x34, 0x12])
            )

            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testUpload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x09, 0x00, 0x01, 0x00, 0xFF, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08])

            res = xm.upload(8)

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x01, 0x00, 0xF5, 0x08]))

        assert res == b"\x01\x02\x03\x04\x05\x06\x07\x08"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testShortUpload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("09 00 01 00 FF 01 02 03 04 05 06 07 08")

            res = xm.shortUpload(8, 0xCAFEBABE, 1)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x01, 0x00, 0xF4, 0x08, 0x00, 0x01, 0xBE, 0xBA, 0xFE, 0xCA])
            )

            assert res == b"\x01\x02\x03\x04\x05\x06\x07\x08"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testBuildChecksum(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("08 00 01 00 FF 09 00 00 04 05 06 07")

            res = xm.buildChecksum(1024)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x01, 0x00, 0xF3, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00])
            )

            assert res.checksumType == types.BuildChecksumResponse.checksumType.XCP_CRC_32
            assert res.checksum == 0x07060504

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testTransportLayerCmd(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x03, 0x00, 0x01, 0x00, 0xFF, 0xAA, 0xBB])

            data = [0xBE, 0xEF]
            res = xm.transportLayerCmd(0x55, data)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x01, 0x00, 0xF2, 0x55, 0xBE, 0xEF]))

        assert res == b"\xaa\xbb"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testUserCmd(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x03, 0x00, 0x01, 0x00, 0xFF, 0xAA, 0xBB])

            data = [0xBE, 0xEF]
            res = xm.userCmd(0x55, data)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x01, 0x00, 0xF1, 0x55, 0xBE, 0xEF]))

        assert res == b"\xaa\xbb"

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testGetVersion(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 00 01 05 01 04")

            res = xm.getVersion()

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x01, 0x00, 0xC0, 0x00]))

            assert res.protocolMajor == 1
            assert res.protocolMinor == 5
            assert res.transportMajor == 1
            assert res.transportMinor == 4

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testDownload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x01, 0x00, 0x01, 0x00, 0xFF])

            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.download(data)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xF0, 0x04, 0xCA, 0xFE, 0xBA, 0xBE])
            )

        assert res == b""

    def testDownloadBlock(self):
        conf = {
            "CAN_ID_MASTER": 1,
            "CAN_ID_SLAVE": 2,
            "CAN_DRIVER": "MockCanInterface",
            "CAN_USE_DEFAULT_LISTENER": False,
        }
        with Master("can", config=conf) as xm:
            mock_caninterface = xm.transport.canInterface
            mock_caninterface.push_packet(self.DefaultConnectResponse)
            xm.connect()

            data = bytes([i for i in range(14)])
            # Downloading 14 bytes in block mode:
            #                               command code    n   payload...
            #  testing ->   DOWNLOAD:       0xF0,           14, 0, 1, 2, 3, 4, 5
            #               DOWNLOAD_NEXT:  0xEF,           8,  6, 7, 8, 9, 10,11
            #               DOWNLOAD_NEXT:  0xEF,           2,  12,13
            # DOWNLOAD service with block mode, this is the first DOWNLOAD packet of a block, no response
            # is expected from the slave device:
            res = xm.download(data=data, blockModeLength=len(data))
            assert res is None

            # DOWNLOAD service with normal mode, normal response expected
            mock_caninterface.push_packet("FF")
            res = xm.download(data=data, blockModeLength=None)
            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testDownloadNext(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x01, 0x00, 0x01, 0x00, 0xFF])

            data = [0xCA, 0xFE, 0xBA, 0xBE]
            remaining_block_length = 42
            res = xm.downloadNext(data, remainingBlockLength=remaining_block_length)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xEF, remaining_block_length, 0xCA, 0xFE, 0xBA, 0xBE])
            )

        # no response shall be expected if it is not the last DOWNLOAD_NEXT packet of a block
        assert res is None

    def testDownloadNextBlock(self):
        conf = {
            "CAN_ID_MASTER": 1,
            "CAN_ID_SLAVE": 2,
            "CAN_DRIVER": "MockCanInterface",
            "CAN_USE_DEFAULT_LISTENER": False,
        }
        with Master("can", config=conf) as xm:
            mock_caninterface = xm.transport.canInterface
            mock_caninterface.push_packet(self.DefaultConnectResponse)
            xm.connect()

            data = bytes([i for i in range(14)])
            #  Downloading 14 bytes in block mode:
            #                               command code    n   payload...
            #               DOWNLOAD:       0xF0,           14, 0, 1, 2, 3, 4, 5
            #  testing ->   DOWNLOAD_NEXT:  0xEF,           8,  6, 7, 8, 9, 10,11
            #  testing ->   DOWNLOAD_NEXT:  0xEF,           2,  12,13

            # This is the first DOWNLOAD_NEXT packet of a block, no response is expected from the slave device.
            res = xm.downloadNext(data=data, remainingBlockLength=8, last=False)
            assert res is None

            # This is the last DOWNLOAD_NEXT packet of a block, positive response is expected from the slave device.
            mock_caninterface.push_packet("FF")
            res = xm.downloadNext(data=data, remainingBlockLength=2, last=True)
            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testDownloadMax(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x01, 0x00, 0x01, 0x00, 0xFF])

            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.downloadMax(data)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x01, 0x00, 0xEE, 0xCA, 0xFE, 0xBA, 0xBE])
            )

        assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testShortDownload(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("01 00 01 00 FF")

            data = [0xCA, 0xFE, 0xBA, 0xBE]
            res = xm.shortDownload(0x12345678, 0x55, data)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x0C, 0x00, 0x01, 0x00, 0xED, 0x04, 0x00, 0x55, 0x78, 0x56, 0x34, 0x12, 0xCA, 0xFE, 0xBA, 0xBE])
            )

            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testModifyBits(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame("01 00 01 00 ff")

            res = xm.modifyBits(0xFF, 0x1234, 0xABCD)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xEC, 0xFF, 0x34, 0x12, 0xCD, 0xAB])
            )

            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testPagCommands(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF")

            res = xm.setCalPage(0x03, 0x12, 0x34)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x01, 0x00, 0xEB, 0x03, 0x12, 0x34]))

            assert res == b""

            ms.push_packet("FF 00 00 55")

            res = xm.getCalPage(0x02, 0x44)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x02, 0x00, 0xEA, 0x02, 0x44]))

            assert res == 0x55

            ms.push_packet("FF 10 01")

            res = xm.getPagProcessorInfo()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x03, 0x00, 0xE9]))

            assert res.maxSegments == 16
            assert res.pagProperties == 0x01

            ms.push_packet("FF 00 00 00 78 56 34 12")

            res = xm.getSegmentInfo(0, 5, 1, 0)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x04, 0x00, 0xE8, 0x00, 0x05, 0x01, 0x00])
            )

            assert res.basicInfo == 0x12345678

            ms.push_packet("FF aa bb cc 78 56")

            res = xm.getSegmentInfo(1, 5, 0, 0)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x05, 0x00, 0xE8, 0x01, 0x05, 0x00, 0x00])
            )

            assert res.maxPages == 0xAA
            assert res.addressExtension == 0xBB
            assert res.maxMapping == 0xCC
            assert res.compressionMethod == 0x78
            assert res.encryptionMethod == 0x56

            ms.push_packet("FF 00 00 00 78 56 34 12")

            res = xm.getSegmentInfo(2, 5, 1, 3)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x06, 0x00, 0xE8, 0x02, 0x05, 0x01, 0x03])
            )

            assert res.mappingInfo == 0x12345678

            ms.push_packet("FF 3F 55")

            res = xm.getPageInfo(0x12, 0x34)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x07, 0x00, 0xE7, 0x00, 0x12, 0x34]))

            assert res[0].xcpWriteAccessWithEcu
            assert res[1] == 0x55

            ms.push_packet("FF")

            res = xm.setSegmentMode(0x01, 0x23)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x08, 0x00, 0xE6, 0x01, 0x23]))

            assert res == b""

            ms.push_packet("FF 00 01")

            res = xm.getSegmentMode(0x23)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x09, 0x00, 0xE5, 0x00, 0x23]))

            assert res == 0x01

            ms.push_packet("FF")

            res = xm.copyCalPage(0x12, 0x34, 0x56, 0x78)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x0A, 0x00, 0xE4, 0x12, 0x34, 0x56, 0x78])
            )

            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testDaqCommands(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_frame([0x01, 0x00, 0x01, 0x00, 0xFF])

            res = xm.setDaqPtr(2, 3, 4)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xE2, 0x00, 0x02, 0x00, 0x03, 0x04])
            )

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x02, 0x00, 0xFF])

            res = xm.writeDaq(31, 15, 1, 0x12345678)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x02, 0x00, 0xE1, 0x1F, 0x0F, 0x01, 0x78, 0x56, 0x34, 0x12])
            )

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x03, 0x00, 0xFF])

            res = xm.setDaqListMode(0x3B, 256, 512, 1, 0xFF)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x03, 0x00, 0xE0, 0x3B, 0x00, 0x01, 0x00, 0x02, 0x01, 0xFF])
            )

            assert res == b""

            ms.push_frame([0x02, 0x00, 0x04, 0x00, 0xFF, 0x00])

            res = xm.startStopDaqList(1, 512)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x04, 0x00, 0xDE, 0x01, 0x00, 0x02]))

            assert res.firstPid == 0

            ms.push_frame([0x01, 0x00, 0x05, 0x00, 0xFF])

            res = xm.startStopSynch(3)

            mock_socket.return_value.send.assert_called_with(bytes([0x02, 0x00, 0x05, 0x00, 0xDD, 0x03]))

            assert res == b""

            ms.push_packet("FF")

            res = xm.writeDaqMultiple(
                [
                    dict(bitOffset=1, size=2, address=3, addressExt=4),
                    dict(bitOffset=5, size=6, address=0x12345678, addressExt=7),
                ]
            )

            mock_socket.return_value.send.assert_called_with(
                bytes(
                    [
                        0x12,
                        0x00,
                        0x06,
                        0x00,
                        0xC7,
                        0x02,
                        0x01,
                        0x02,
                        0x03,
                        0x00,
                        0x00,
                        0x00,
                        0x04,
                        0x00,
                        0x05,
                        0x06,
                        0x78,
                        0x56,
                        0x34,
                        0x12,
                        0x07,
                        0x00,
                    ]
                )
            )

            assert res == b""

            ms.push_frame("08 00 07 00 FF 1F 03 04 78 56 34 12")

            res = xm.readDaq()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x07, 0x00, 0xDB]))

            assert res.bitOffset == 31
            assert res.sizeofDaqElement == 3
            assert res.adressExtension == 4
            assert res.address == 0x12345678

            ms.push_frame("08 00 08 00 FF 00 03 04 78 56 34 12")

            res = xm.getDaqClock()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x08, 0x00, 0xDC]))

            # todo: assert res.triggerInfo ==
            # todo: assert res.payloadFmt ==
            # todo: assert res.timestamp == 0x12345678
            assert res == 0x12345678

            ms.push_frame("08 00 09 00 FF 55 00 01 34 12 22 03")

            res = xm.getDaqProcessorInfo()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x09, 0x00, 0xDA]))

            assert res.daqProperties.overloadMsb is True
            assert res.daqProperties.bitStimSupported is False
            assert res.maxDaq == 256
            assert res.maxEventChannel == 0x1234
            assert res.minDaq == 0x22
            assert res.daqKeyByte.Optimisation_Type == "OM_ODT_TYPE_64"

            ms.push_frame("08 00 0A 00 FF 12 34 56 78 AA 34 12")

            res = xm.getDaqResolutionInfo()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x0A, 0x00, 0xD9]))

            assert res.granularityOdtEntrySizeDaq == 0x12
            assert res.maxOdtEntrySizeDaq == 0x34
            assert res.granularityOdtEntrySizeStim == 0x56
            assert res.maxOdtEntrySizeStim == 0x78
            assert res.timestampMode.size == "S2"
            assert res.timestampMode.fixed is True
            assert res.timestampMode.unit == "DAQ_TIMESTAMP_UNIT_1PS"
            assert res.timestampTicks == 0x1234

            ms.push_frame("08 00 0B 00 FF AA 00 00 34 12 56 78")

            res = xm.getDaqListMode(256)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x0B, 0x00, 0xDF, 0x00, 0x00, 0x01]))

            assert res.currentMode.resume is True
            assert res.currentMode.selected is False
            assert res.currentEventChannel == 0x1234
            assert res.currentPrescaler == 0x56
            assert res.currentPriority == 0x78

            ms.push_frame("07 00 0C 00 FF 48 EE 05 06 07 FF")

            res = xm.getDaqEventInfo(256)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x0C, 0x00, 0xD7, 0x00, 0x00, 0x01]))

            assert res.daqEventProperties.consistency == "CONSISTENCY_DAQ"
            assert res.daqEventProperties.stim is True
            assert res.daqEventProperties.daq is False
            assert res.maxDaqList == 0xEE
            assert res.eventChannelNameLength == 0x05
            assert res.eventChannelTimeCycle == 0x06
            assert res.eventChannelTimeUnit == "EVENT_CHANNEL_TIME_UNIT_10MS"
            assert res.eventChannelPriority == 0xFF

            ms.push_packet("FF AA 34 12 02")

            res = xm.dtoCtrProperties(0x05, 0x1234, 0x5678, 0x02)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x07, 0x00, 0x0D, 0x00, 0xC5, 0x05, 0x34, 0x12, 0x78, 0x56, 0x02])
            )

            assert res.properties.evtCtrPresent is True
            assert res.properties.relatedEventFixed is False
            assert res.relatedEventChannel == 0x1234
            assert res.mode.stimMode is True
            assert res.mode.daqMode is False

            ms.push_frame([0x01, 0x00, 0x0E, 0x00, 0xFF])

            res = xm.clearDaqList(256)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x0E, 0x00, 0xE3, 0x00, 0x00, 0x01]))

            assert res == b""

            ms.push_frame("06 00 0F 00 FF 15 10 20 34 12")

            res = xm.getDaqListInfo(256)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x0F, 0x00, 0xD8, 0x00, 0x00, 0x01]))

            assert res.daqListProperties.packed is True
            assert res.daqListProperties.eventFixed is False
            assert res.maxOdt == 0x10
            assert res.maxOdt == 0x10
            assert res.maxOdtEntries == 0x20
            assert res.fixedEvent == 0x1234

            ms.push_frame([0x01, 0x00, 0x10, 0x00, 0xFF])

            res = xm.freeDaq()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x10, 0x00, 0xD6]))

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x11, 0x00, 0xFF])

            res = xm.allocDaq(258)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x11, 0x00, 0xD5, 0x00, 0x02, 0x01]))

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x12, 0x00, 0xFF])

            res = xm.allocOdt(258, 3)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x12, 0x00, 0xD4, 0x00, 0x02, 0x01, 0x03])
            )

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x13, 0x00, 0xFF])

            res = xm.allocOdtEntry(258, 3, 4)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x13, 0x00, 0xD3, 0x00, 0x02, 0x01, 0x03, 0x04])
            )

            assert res == b""

            ms.push_frame([0x01, 0x00, 0x14, 0x00, 0xFF])

            res = xm.setDaqPackedMode(258, 0)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x14, 0x00, 0xC0, 0x01, 0x02, 0x01, 0x00])
            )

            assert res == b""

            ms.push_frame([0x03, 0x00, 0x15, 0x00, 0xFF, 0x00, 0x00])

            res = xm.getDaqPackedMode(258)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x15, 0x00, 0xC0, 0x02, 0x02, 0x01]))

            assert res.daqPackedMode == types.DaqPackedMode.NONE
            assert res.dpmTimestampMode is None

            ms.push_frame([0x01, 0x00, 0x16, 0x00, 0xFF])

            res = xm.setDaqPackedMode(258, 2, 0b01, 0x1234)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x16, 0x00, 0xC0, 0x01, 0x02, 0x01, 0x02, 0x01, 0x34, 0x12])
            )

            assert res == b""

            ms.push_frame("06 00 17 00 FF 00 02 01 34 12")

            res = xm.getDaqPackedMode(258)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x17, 0x00, 0xC0, 0x02, 0x02, 0x01]))

            assert res.daqPackedMode == "EVENT_GROUPED"
            assert res.dpmTimestampMode == 0x01
            assert res.dpmSampleCount == 0x1234

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testPgmCommands(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet(b"\xFF\x00\x01\x08\x2A\xFF\x55")

            res = xm.programStart()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x01, 0x00, 0xD2]))

            assert res.commModePgm.masterBlockMode is True
            assert res.commModePgm.interleavedMode is False
            assert res.commModePgm.slaveBlockMode is False
            assert res.maxCtoPgm == 8
            assert res.maxBsPgm == 0x2A
            assert res.minStPgm == 0xFF
            assert res.queueSizePgm == 0x55

            ms.push_packet("FF")

            res = xm.programClear(0x00, 0xA0000100)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x02, 0x00, 0xD1, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0xA0])
            )

            assert res == b""

            ms.push_packet("FF")

            res = xm.program([0x01, 0x02, 0x03, 0x04])

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x03, 0x00, 0xD0, 0x04, 0x01, 0x02, 0x03, 0x04])
            )

            assert res == b""

            ms.push_packet("FF")

            res = xm.programReset()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x04, 0x00, 0xCF]))

            assert res == b""

            ms.push_packet("FF AA BB")

            res = xm.getPgmProcessorInfo()

            mock_socket.return_value.send.assert_called_with(bytes([0x01, 0x00, 0x05, 0x00, 0xCE]))

            assert res.pgmProperties.nonSeqPgmRequired is True
            assert res.pgmProperties.nonSeqPgmSupported is False
            assert res.maxSector == 0xBB

            ms.push_packet("FF AA BB CC 78 56 34 12")

            res = xm.getSectorInfo(0, 0x12)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x06, 0x00, 0xCD, 0, 0x12]))

            assert res.clearSequenceNumber == 0xAA
            assert res.programSequenceNumber == 0xBB
            assert res.programmingMethod == 0xCC
            assert res.sectorInfo == 0x12345678

            ms.push_packet("FF AA")

            res = xm.getSectorInfo(2, 0x12)

            mock_socket.return_value.send.assert_called_with(bytes([0x03, 0x00, 0x07, 0x00, 0xCD, 2, 0x12]))

            assert res.sectorNameLength == 0xAA

            ms.push_packet("FF")

            res = xm.programPrepare(0x1234)

            mock_socket.return_value.send.assert_called_with(bytes([0x04, 0x00, 0x08, 0x00, 0xCC, 0x00, 0x34, 0x12]))

            assert res == b""

            ms.push_packet("FF")

            res = xm.programFormat(0x81, 0x82, 0x83, 0x01)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x09, 0x00, 0xCB, 0x81, 0x82, 0x83, 0x01])
            )

            assert res == b""

            ms.push_packet("FF")

            res = xm.programNext([0x01, 0x02, 0x03, 0x04])

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x0A, 0x00, 0xCA, 0x04, 0x01, 0x02, 0x03, 0x04])
            )

            assert res == b""

            ms.push_packet("FF")

            res = xm.programMax([0x01, 0x02, 0x03, 0x04])

            mock_socket.return_value.send.assert_called_with(
                bytes([0x05, 0x00, 0x0B, 0x00, 0xC9, 0x01, 0x02, 0x03, 0x04])
            )

            assert res == b""

            ms.push_packet("FF")

            res = xm.programVerify(0x01, 0x0004, 0xCAFEBABE)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x08, 0x00, 0x0C, 0x00, 0xC8, 0x01, 0x04, 0x00, 0xBE, 0xBA, 0xFE, 0xCA])
            )

            assert res == b""

    @mock.patch("pyxcp.transport.eth.socket.socket")
    @mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
    def testTimeCorrelationProperties(self, mock_selector, mock_socket):
        ms = MockSocket()

        mock_socket.return_value.recv.side_effect = ms.recv
        mock_selector.return_value.select.side_effect = ms.select

        with Master("eth", config={"HOST": "localhost", "LOGLEVEL": "DEBUG"}) as xm:
            ms.push_packet(self.DefaultConnectResponse)

            res = xm.connect()

            mock_socket.return_value.send.assert_called_with(self.DefaultConnectCmd)

            ms.push_packet("FF 15 25 01 1F 00 78 56")

            res = xm.timeCorrelationProperties(0x15, 0x01, 0x1234)

            mock_socket.return_value.send.assert_called_with(
                bytes([0x06, 0x00, 0x01, 0x00, 0xC6, 0x15, 0x01, 0x00, 0x34, 0x12])
            )

            assert res.slaveConfig == 0x15
            assert res.observableClocks == 0x25
            assert res.syncState == 0x01
            assert res.clockInfo == 0x1F
            assert res.clusterId == 0x5678
