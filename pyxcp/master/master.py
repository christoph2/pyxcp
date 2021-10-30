#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Lowlevel API reflecting available XCP services.

.. note:: For technical reasons the API is split into two parts;
          common methods (this file) and a Python version specific part.

.. [1] XCP Specification, Part 2 - Protocol Layer Specification
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2021 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import logging
import struct
import traceback
import warnings
from time import sleep

from pyxcp import checksum
from pyxcp import types
from pyxcp.config import Configuration
from pyxcp.constants import makeBytePacker, makeByteUnpacker, makeWordPacker, makeWordUnpacker, makeDWordPacker, makeDWordUnpacker, makeDLongPacker, makeDLongUnpacker
from pyxcp.master.errorhandler import wrapped
from pyxcp.transport.base import createTransport


def broadcasted(func):
    """"""
    return func


class SlaveProperties(dict):
    """Container class for fixed parameters, like byte-order, maxCTO, ..."""

    def __init__(self, *args, **kws):
        super(SlaveProperties, self).__init__(*args, **kws)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self = state

class Master:
    """Common part of lowlevel XCP API.

    Parameters
    ----------
    transportName : str
        XCP transport layer name ['can', 'eth', 'sxi']
    config: dict
    """

    PARAMETER_MAP = {
        #            Type Req'd  Default
        "LOGLEVEL": (str, False, "WARN"),
    }

    def __init__(self, transportName, config=None):
        self.ctr = 0
        self.succeeded = True
        self.config = Configuration(self.PARAMETER_MAP or {}, config or {})
        self.logger = logging.getLogger("pyXCP")
        self.logger.setLevel(self.config.get("LOGLEVEL"))
        self.transport = createTransport(transportName, config)
        self.transport_name = transportName

        # In some cases the transport-layer needs to communicate with us.
        self.transport.parent = self
        self.service = None

        # (D)Word (un-)packers are byte-order dependent
        # -- byte-order is returned by CONNECT_Resp (COMM_MODE_BASIC)
        self.BYTE_pack = None
        self.BYTE_unpack = None
        self.WORD_pack = None
        self.WORD_unpack = None
        self.DWORD_pack = None
        self.DWORD_unpack = None
        self.DLONG_pack = None
        self.DLONG_unpack = None
        self.AG_pack = None
        self.AG_unpack = None
        # self.connected = False
        self.mta = types.MtaType(None, None)
        self.currentDaqPtr = None
        self.currentProtectionStatus = None
        self._seedNKeyDLL = None

    def __enter__(self):
        """Context manager entry part."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit part."""
        # if self.connected:
        #    self.disconnect()
        self.close()
        if exc_type is None:
            return
        else:
            self.succeeded = False
            # print("=" * 79)
            # print("Exception while in Context-Manager:\n")
            self.logger.error("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))
            # print("=" * 79)
            # return True

    def _setService(self, service):
        """Records the currently processed service.

        Parameters
        ----------
        service: `pydbc.types.Command`

        Note
        ----
        Internal Function, only to be used by transport-layer.
        """
        self.service = service

    def close(self):
        """Closes transport layer connection."""
        self.transport.close()

    # Mandatory Commands.
    @wrapped
    def connect(self, mode=0x00):
        """Build up connection to an XCP slave.

        Before the actual XCP traffic starts a connection is required.

        Parameters
        ----------
        mode : int
            connection mode; default is 0x00 (normal mode)

        Returns
        -------
        :py:obj:`pyxcp.types.ConnectResponse`
            Describes fundamental client properties.

        Note
        ----
        Every XCP slave supports at most one connection,
        more attempts to connect are silently ignored.

        """
        self.transport.connect()

        response = self.transport.request(types.Command.CONNECT, mode & 0xFF)

        # First get byte-order
        resultPartial = types.ConnectResponsePartial.parse(response)
        byteOrder = resultPartial.commModeBasic.byteOrder

        result = types.ConnectResponse.parse(response, byteOrder=byteOrder)
        self.slaveProperties = SlaveProperties(byteOrder=byteOrder, maxCto=result.maxCto, maxDto=result.maxDto)
        byteOrderPrefix = "<" if byteOrder == types.ByteOrder.INTEL else ">"

        self.slaveProperties.supportsPgm = result.resource.pgm
        self.slaveProperties.supportsStim = result.resource.stim
        self.slaveProperties.supportsDaq = result.resource.daq
        self.slaveProperties.supportsCalpag = result.resource.calpag
        self.slaveProperties.slaveBlockMode = result.commModeBasic.slaveBlockMode
        self.slaveProperties.addressGranularity = result.commModeBasic.addressGranularity
        self.slaveProperties.protocolLayerVersion = result.protocolLayerVersion
        self.slaveProperties.transportLayerVersion = result.transportLayerVersion
        self.slaveProperties.optionalCommMode = result.commModeBasic.optional
        self.slaveProperties.maxWriteDaqMultipleElements = (
            0 if self.slaveProperties.maxCto < 10 else int((self.slaveProperties.maxCto - 2) // 8)
        )

        self.BYTE_pack = makeBytePacker(byteOrderPrefix)
        self.BYTE_unpack = makeByteUnpacker(byteOrderPrefix)
        self.WORD_pack = makeWordPacker(byteOrderPrefix)
        self.WORD_unpack = makeWordUnpacker(byteOrderPrefix)
        self.DWORD_pack = makeDWordPacker(byteOrderPrefix)
        self.DWORD_unpack = makeDWordUnpacker(byteOrderPrefix)
        self.DLONG_pack = makeDLongPacker(byteOrderPrefix)
        self.DLONG_unpack = makeDLongUnpacker(byteOrderPrefix)

        if self.slaveProperties.addressGranularity == types.AddressGranularity.BYTE:
            self.AG_pack = struct.Struct("<B").pack
            self.AG_unpack = struct.Struct("<B").unpack
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.WORD:
            self.AG_pack = self.WORD_pack
            self.AG_unpack = self.WORD_unpack
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            self.AG_pack = self.DWORD_pack
            self.AG_unpack = self.DWORD_unpack
        # self.connected = True
        return result

    @wrapped
    def disconnect(self):
        """Releases the connection to the XCP slave.

        Thereafter, no further communication with the slave is possible
        (besides `connect`).


        Note
        -----
        If DISCONNECT is currently not possible, ERR_CMD_BUSY will be returned.
        """
        response = self.transport.request(types.Command.DISCONNECT)
        # self.connected = False
        return response

    @wrapped
    def getStatus(self):
        """Get current status information of the slave device.

        This includes the status of the resource protection, pending store
        requests and the general status of data acquisition and stimulation.

        Returns
        -------
        :obj:`pyxcp.types.GetStatusResponse`
        """
        response = self.transport.request(types.Command.GET_STATUS)
        result = types.GetStatusResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self._setProtectionStatus(result.resourceProtectionStatus)
        return result

    @wrapped
    def synch(self):
        """Synchronize command execution after timeout conditions."""
        response = self.transport.request(types.Command.SYNCH)
        return response

    @wrapped
    def getCommModeInfo(self):
        """Get optional information on different Communication Modes supported
        by the slave.

        Returns
        -------
        :obj:`pyxcp.types.GetCommModeInfoResponse`
        """
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)
        result = types.GetCommModeInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.interleavedMode = result.commModeOptional.interleavedMode
        self.slaveProperties.masterBlockMode = result.commModeOptional.masterBlockMode
        self.slaveProperties.maxBs = result.maxBs
        self.slaveProperties.minSt = result.minSt
        self.slaveProperties.queueSize = result.queueSize
        self.slaveProperties.xcpDriverVersionNumber = result.xcpDriverVersionNumber
        return result

    @wrapped
    def getId(self, mode: int):
        """This command is used for automatic session configuration and for
        slave device identification.

        Parameters
        ----------
        mode : int
            The following identification types may be requested:
            - 0        ASCII text
            - 1        ASAM-MC2 filename without path and extension
            - 2        ASAM-MC2 filename with path and extension
            - 3        URL where the ASAM-MC2 file can be found
            - 4        ASAM-MC2 file to upload
            - 128..255 User defined

        Returns
        -------
        :obj:`pydbc.types.GetIDResponse`
        """
        response = self.transport.request(types.Command.GET_ID, mode)
        result = types.GetIDResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        result.length = self.DWORD_unpack(response[3:7])[0]
        return result

    @wrapped
    def setRequest(self, mode: int, sessionConfigurationId: int):
        """Request to save to non-volatile memory.

        Parameters
        ----------
        mode : int (bitfield)
            - 1  Request to store calibration data
            - 2  Request to store DAQ list, no resume
            - 4  Request to store DAQ list, resume enabled
            - 8  Request to clear DAQ configuration
        sessionConfigurationId : int

        """
        return self.transport.request(
            types.Command.SET_REQUEST, mode, sessionConfigurationId >> 8, sessionConfigurationId & 0xFF
        )

    @wrapped
    def getSeed(self, first: int, resource: int):
        """Get seed from slave for unlocking a protected resource.

        Parameters
        ----------
        first : int
            - 0 - first part of seed
            - 1 - remaining part
        resource : int
            - Mode = =0 - Resource
            - Mode == 1 - Don't care

        Returns
        -------
        `pydbc.types.GetSeedResponse`
        """
        if self.transport_name == 'can':
            # for CAN it might happen that the seed is longer than the max DLC
            # in this case the first byte will be the current remaining seed size
            # followed by the seeds bytes that can fit in the current frame
            # the master must call getSeed several times until the complete seed is received
            response = self.transport.request(types.Command.GET_SEED, first, resource)
            size, seed = response[0], response[1:]
            if size < len(seed):
                seed = seed[:size]
            reply = types.GetSeedResponse.parse(
                types.GetSeedResponse.build({"leght": size, "seed": bytes(size)}),
                byteOrder = self.slaveProperties.byteOrder
            )
            reply.seed = seed
            return reply
        else:
            response = self.transport.request(types.Command.GET_SEED, first, resource)
            return types.GetSeedResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def unlock(self, length: int, key: bytes):
        """Send key to slave for unlocking a protected resource.

        Parameters
        ----------
        length : int
            indicates the (remaining) number of key bytes.
        key : bytes

        Returns
        -------
        :obj:`pydbc.types.ResourceType`

        Note
        ----
        The master has to use :meth:`unlock` in a defined sequence together
        with :meth:`getSeed`. The master only can send an :meth:`unlock` sequence
        if previously there was a :meth:`getSeed` sequence. The master has
        to send the first `unlocking` after a :meth:`getSeed` sequence with
        a Length containing the total length of the key.
        """
        response = self.transport.request(types.Command.UNLOCK, length, *key)
        result = types.ResourceType.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self._setProtectionStatus(result)
        return result

    @wrapped
    def setMta(self, address: int, addressExt: int = 0x00):
        """Set Memory Transfer Address in slave.

        Parameters
        ----------
        address : int
        addressExt : int

        Note
        ----
        The MTA is used by :meth:`buildChecksum`, :meth:`upload`, :meth:`download`, :meth:`downloadNext`,
        :meth:`downloadMax`, :meth:`modifyBits`, :meth:`programClear`, :meth:`program`, :meth:`programNext`
        and :meth:`programMax`.

        """
        self.mta = types.MtaType(address, addressExt)  # Keep track of MTA (needed for error-handling).
        addr = self.DWORD_pack(address)
        return self.transport.request(types.Command.SET_MTA, 0, 0, addressExt, *addr)

    @wrapped
    def upload(self, length: int):
        """Transfer data from slave to master.

        Parameters
        ----------
        length : int

        Note
        ----
        Adress is set via :meth:`setMta` (Some services like :meth:`getID` also set the MTA).

        Returns
        -------
        bytes
        """

        response = self.transport.request(types.Command.UPLOAD, length)
        if length > (self.slaveProperties.maxCto - 1):
            block_response = self.transport.block_receive(length_required=(length - len(response)))
            response += block_response
        elif self.transport_name == 'can':
            # larger sizes will send in multiple CAN messages
            # each valid message will start with 0xFF followed by the upload bytes
            # the last message might be padded to the required DLC
            rem = length - len(response)
            while rem:
                if len(self.transport.resQueue):
                    data = self.transport.resQueue.popleft()
                    response += data[1:rem + 1]
                    rem = length - len(response)
                else:
                    sleep(0.001)

        return response

    @wrapped
    def shortUpload(self, length: int, address: int, addressExt: int = 0x00):
        """Transfer data from slave to master.
        As opposed to :meth:`upload` this service also includes address information.

        Parameters
        ----------
        address : int
        addressExt : int

        Returns
        -------
        bytes
        """
        addr = self.DWORD_pack(address)
        return self.transport.request(types.Command.SHORT_UPLOAD, length, 0, addressExt, *addr)

    @wrapped
    def buildChecksum(self, blocksize: int):
        """Build checksum over memory range.

        Parameters
        ----------
        blocksize : int

        Returns
        -------
        :obj:`~pyxcp.types.BuildChecksumResponse`

        .. note:: Adress is set via `setMta`

        See Also
        --------
        :mod:`~pyxcp.checksum`
        """
        bs = self.DWORD_pack(blocksize)
        response = self.transport.request(types.Command.BUILD_CHECKSUM, 0, 0, 0, *bs)
        return types.BuildChecksumResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def transportLayerCmd(self, subCommand: int, data: bytes):
        """Execute transfer-layer specific command.

        Parameters
        ----------
        subCommand : int
        data : bytes

        Note
        ----
        For details refer to XCP specification.
        """
        return self.transport.request(types.Command.TRANSPORT_LAYER_CMD, subCommand, *data)

    @wrapped
    def userCmd(self, subCommand: int, data: bytes):
        """Execute proprietary command implemented in your XCP client.

        Parameters
        ----------
        subCommand : int
        data : bytes


        .. note:: For details refer to your XCP client vendor.
        """

        response = self.transport.request(types.Command.USER_CMD, subCommand, *data)
        return response

    @wrapped
    def getVersion(self):
        """Get version information.

        This command returns detailed information about the implemented
        protocol layer version of the XCP slave and the transport layer
        currently in use.

        Returns
        -------
        :obj:`~types.GetVersionResponse`
        """

        response = self.transport.request(types.Command.GET_VERSION)
        result = types.GetVersionResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.protocolMajor = result.protocolMajor
        self.slaveProperties.protocolMinor = result.protocolMinor
        self.slaveProperties.transportMajor = result.transportMajor
        self.slaveProperties.transportMinor = result.transportMinor
        return result

    def fetch(self, length: int, limitPayload: int = None):  # TODO: pull
        """Convenience function for data-transfer from slave to master
        (Not part of the XCP Specification).

        Parameters
        ----------
        length : int
        limitPayload : int
            transfer less bytes then supported by transport-layer

        Returns
        -------
        bytes

        Note
        ----
        address is not included because of services implicitly setting address information like :meth:`getID` .
        """
        if limitPayload and limitPayload < 8:
            raise ValueError("Payload must be at least 8 bytes - given: {}".format(limitPayload))

        slaveBlockMode = self.slaveProperties.slaveBlockMode
        if slaveBlockMode:
            maxPayload = 255
        else:
            maxPayload = self.slaveProperties.maxCto - 1
        payload = min(limitPayload, maxPayload) if limitPayload else maxPayload
        chunkSize = payload
        chunks = range(length // chunkSize)
        remaining = length % chunkSize
        result = []
        for _ in chunks:
            data = self.upload(chunkSize)
            result.extend(data)
        if remaining:
            data = self.upload(remaining)
            result.extend(data)
        return bytes(result)

    pull = fetch  # fetch() may be completely replaced by pull() someday.

    def push(self, data: bytes):
        """Convenience function for data-transfer from master to slave.
        (Not part of the XCP Specification).

        Parameters
        ----------
        data : bytes
            Arbitrary number of bytes.

        Returns
        -------

        Note
        ----
        address is not included because of services implicitly setting address information like :meth:`getID` .
        """
        # TODO: consider minST.

        total_length = len(data)
        master_block_mode = self.slaveProperties.masterBlockMode
        if master_block_mode:
            max_payload = min(self.slaveProperties.maxBs * (self.slaveProperties.maxCto - 2), 255)
        else:
            max_payload = self.slaveProperties.maxCto - 2
        offset = 0
        if master_block_mode:
            payload_length = self.slaveProperties.maxCto - 2
            rem2 = total_length
            blocks = range(total_length // max_payload)
            remaining_block_size = total_length % max_payload
            for idx in blocks:
                data_slice = data[offset : offset + max_payload]
                self._block_downloader(data_slice)
                offset += max_payload
                rem2 -= max_payload
            if remaining_block_size:
                data_slice = data[offset : offset + remaining_block_size]
                self._block_downloader(data_slice)
        else:
            chunk_size = max_payload
            chunks = range(total_length // chunk_size)
            remaining = total_length % chunk_size
            for _ in chunks:
                frame_data = data[offset : offset + max_payload]
                self.download(frame_data, max_payload)
                offset += max_payload
            if remaining:
                frame_data = data[offset : offset + remaining]
                self.download(frame_data, remaining)

    def _block_downloader(self, data: bytes):
        """"""
        length = len(data)
        payload_length = self.slaveProperties.maxCto - 2
        chunks = range(length // payload_length)
        offset = 0
        remaining = length % payload_length
        rem2 = length
        idx = 0
        for idx in chunks:
            frame_data = data[offset : offset + payload_length]
            if idx == 0:
                self.download(frame_data, length)  # Transmit the complete length in the first CTO.
            else:
                self.downloadNext(frame_data, rem2)
            offset += payload_length
            rem2 -= payload_length
        if remaining:
            frame_data = data[offset : offset + remaining]
            if idx == 0:
                # length of data is smaller than maxCto - 2
                self.download(frame_data, remaining)
            else:
                self.downloadNext(frame_data, remaining)

    @wrapped
    def download(self, data: bytes, blockModeLength=None):
        """Transfer data from master to slave.

        Parameters
        ----------
        data : bytes
            Data to send to slave.
        blockModeLength : int or None
            for block mode, the download request must contain the length of the whole block,
            not just the length in the current packet. The whole block length can be given here for block-mode
            transfers. For normal mode, the length indicates the actual packet's payload length.

        Note
        ----
        Adress is set via :meth:`setMta`
        """

        if blockModeLength is None:
            # standard mode
            length = len(data)
            response = self.transport.request(types.Command.DOWNLOAD, length, *data)
            return response
        else:
            # block mode
            if not isinstance(blockModeLength, int):
                raise TypeError("blockModeLength must be int!")
            self.transport.block_request(types.Command.DOWNLOAD, blockModeLength, *data)
            return None

    @wrapped
    def downloadNext(self, data: bytes, remainingBlockLength, last=False):
        """Transfer data from master to slave (block mode).

        Parameters
        ----------
        data : bytes
        remainingBlockLength : int
            This parameter has to be given the remaining length in the block
        last : bool
            The block mode implementation shall indicate the last packet in the block with this parameter, because
            the slave device will send the response after this.
        """

        if last:
            # last DOWNLOAD_NEXT packet in a block: the slave device has to send the response after this.
            response = self.transport.request(types.Command.DOWNLOAD_NEXT, remainingBlockLength, *data)
            return response
        else:
            # the slave device won't respond to consecutive DOWNLOAD_NEXT packets in block mode,
            # so we must not wait for any response
            self.transport.block_request(types.Command.DOWNLOAD_NEXT, remainingBlockLength, *data)
            return None

    @wrapped
    def downloadMax(self, data: bytes):
        """Transfer data from master to slave (fixed size).

        Parameters
        ----------
        data : bytes
        """
        return self.transport.request(types.Command.DOWNLOAD_MAX, *data)

    @wrapped
    def shortDownload(self, address, addressExt, data):
        length = len(data)
        addr = self.DWORD_pack(address)
        return self.transport.request(types.Command.SHORT_DOWNLOAD, length, 0, addressExt, *addr, *data)

    @wrapped
    def modifyBits(self, shiftValue, andMask, xorMask):
        # A = ( (A) & ((~((dword)(((word)~MA)<<S))) )^((dword)(MX<<S)) )
        am = self.WORD_pack(andMask)
        xm = self.WORD_pack(xorMask)
        return self.transport.request(types.Command.MODIFY_BITS, shiftValue, *am, *xm)

    # Page Switching Commands (PAG)
    @wrapped
    def setCalPage(self, mode: int, logicalDataSegment: int, logicalDataPage: int):
        """Set calibration page.

        Parameters
        ----------
        mode : int (bitfield)
            - 0x01 - The given page will be used by the slave device application.
            - 0x02 - The slave device XCP driver will access the given page.
            - 0x80 - The logical segment number is ignored. The command applies to all segments
        logicalDataSegment : int
        logicalDataPage : int
        """
        return self.transport.request(types.Command.SET_CAL_PAGE, mode, logicalDataSegment, logicalDataPage)

    @wrapped
    def getCalPage(self, mode: int, logicalDataSegment: int):
        """Get calibration page

        Parameters
        ----------
        mode : int
        logicalDataSegment : int
        """
        response = self.transport.request(types.Command.GET_CAL_PAGE, mode, logicalDataSegment)
        return response[2]

    @wrapped
    def getPagProcessorInfo(self):
        """Get general information on PAG processor.

        Returns
        -------
        `pydbc.types.GetPagProcessorInfoResponse`
        """
        response = self.transport.request(types.Command.GET_PAG_PROCESSOR_INFO)
        return types.GetPagProcessorInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getSegmentInfo(self, mode, segmentNumber, segmentInfo, mappingIndex):
        """Get specific information for a segment.

        Parameters
        ----------
        mode : int
            - 0 = get basic address info for this segment
            - 1 = get standard info for this segment
            - 2 = get address mapping info for this segment

        segmentNumber : int
        segmentInfo : int
            Mode 0:
                - 0 = address
                - 1 = length

            Mode 1:
                - don't care

            Mode 2:
                - 0 = source address
                - 1 = destination address
                - 2 = length address

        mappingIndex : int
            - Mode 0: don't care
            - Mode 1: don't care
            - Mode 2: identifier for address mapping range that mapping_info belongs to.

        """
        response = self.transport.request(
            types.Command.GET_SEGMENT_INFO, mode, segmentNumber, segmentInfo, mappingIndex
        )
        if mode == 0:
            return types.GetSegmentInfoMode0Response.parse(response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 1:
            return types.GetSegmentInfoMode1Response.parse(response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 2:
            return types.GetSegmentInfoMode2Response.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getPageInfo(self, segmentNumber, pageNumber):
        """Get specific information for a page.

        Parameters
        ----------
        segmentNumber : int
        pageNumber : int
        """
        response = self.transport.request(types.Command.GET_PAGE_INFO, 0, segmentNumber, pageNumber)
        return (types.PageProperties.parse(bytes([response[0]]), byteOrder=self.slaveProperties.byteOrder), response[1])

    @wrapped
    def setSegmentMode(self, mode, segmentNumber):
        """Set mode for a segment.

        Parameters
        ----------
        mode : int (bitfield)
            1 = enable FREEZE Mode
        segmentNumber : int
        """
        return self.transport.request(types.Command.SET_SEGMENT_MODE, mode, segmentNumber)

    @wrapped
    def getSegmentMode(self, segmentNumber):
        """Get mode for a segment.

        Parameters
        ----------
        segmentNumber : int
        """
        response = self.transport.request(types.Command.GET_SEGMENT_MODE, 0, segmentNumber)
        return response[1]

    @wrapped
    def copyCalPage(self, srcSegment, srcPage, dstSegment, dstPage):
        """Copy page.

        Parameters
        ----------
        srcSegment : int
        srcPage : int
        dstSegment : int
        dstPage : int
        """
        return self.transport.request(types.Command.COPY_CAL_PAGE, srcSegment, srcPage, dstSegment, dstPage)

    # DAQ

    @wrapped
    def setDaqPtr(self, daqListNumber, odtNumber, odtEntryNumber):
        self.currentDaqPtr = types.DaqPtr(daqListNumber, odtNumber, odtEntryNumber)  # Needed for errorhandling.
        daqList = self.WORD_pack(daqListNumber)
        response = self.transport.request(types.Command.SET_DAQ_PTR, 0, *daqList, odtNumber, odtEntryNumber)
        return response

    @wrapped
    def clearDaqList(self, daqListNumber):
        """Clear DAQ list configuration.

        Parameters
        ----------
        daqListNumber : int
        """
        daqList = self.WORD_pack(daqListNumber)
        return self.transport.request(types.Command.CLEAR_DAQ_LIST, 0, *daqList)

    @wrapped
    def writeDaq(self, bitOffset, entrySize, addressExt, address):
        """Write element in ODT entry.

        Parameters
        ----------
        bitOffset : int
            Position of bit in 32-bit variable referenced by the address and
            extension below
        entrySize : int
        addressExt : int
        address : int
        """
        addr = self.DWORD_pack(address)
        return self.transport.request(types.Command.WRITE_DAQ, bitOffset, entrySize, addressExt, *addr)

    @wrapped
    def setDaqListMode(self, mode, daqListNumber, eventChannelNumber, prescaler, priority):
        dln = self.WORD_pack(daqListNumber)
        ecn = self.WORD_pack(eventChannelNumber)
        return self.transport.request(types.Command.SET_DAQ_LIST_MODE, mode, *dln, *ecn, prescaler, priority)

    @wrapped
    def getDaqListMode(self, daqListNumber):
        """Get mode from DAQ list.

        Parameters
        ----------
        daqListNumber : int

        Returns
        -------
        `pyxcp.types.GetDaqListModeResponse`
        """
        dln = self.WORD_pack(daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def startStopDaqList(self, mode, daqListNumber):
        """Start /stop/select DAQ list.

        Parameters
        ----------
        mode : int
            0 = stop
            1 = start
            2 = select
        daqListNumber : int
        """
        dln = self.WORD_pack(daqListNumber)
        response = self.transport.request(types.Command.START_STOP_DAQ_LIST, mode, *dln)
        return types.StartStopDaqListResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def startStopSynch(self, mode):
        """Start/stop DAQ lists (synchronously).

        Parameters
        ----------
        mode : int
            0 = stop all
            1 = start selected
            2 = stop selected
        """
        return self.transport.request(types.Command.START_STOP_SYNCH, mode)

    @wrapped
    def writeDaqMultiple(self, daqElements):
        """Write multiple elements in ODT.

        Parameters
        ----------
        daqElements : list of `dict` containing the following keys: *bitOffset*, *size*, *address*, *addressExt*.
        """
        if len(daqElements) > self.slaveProperties.maxWriteDaqMultipleElements:
            raise ValueError(
                "At most {} daqElements are permitted.".format(self.slaveProperties.maxWriteDaqMultipleElements)
            )
        data = bytearray()
        data.append(len(daqElements))

        for daqElement in daqElements:
            data.extend(types.DaqElement.build(daqElement, byteOrder=self.slaveProperties.byteOrder))

        return self.transport.request(types.Command.WRITE_DAQ_MULTIPLE, *data)

    # optional
    @wrapped
    def getDaqClock(self):
        """Get DAQ clock from slave.

        Returns
        -------
        int
            Current timestamp, format specified by `getDaqResolutionInfo`
        """
        response = self.transport.request(types.Command.GET_DAQ_CLOCK)
        result = types.GetDaqClockResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        return result.timestamp

    @wrapped
    def readDaq(self):
        """Read element from ODT entry.

        Returns
        -------
        `pyxcp.types.ReadDaqResponse`
        """
        response = self.transport.request(types.Command.READ_DAQ)
        return types.ReadDaqResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqProcessorInfo(self):
        """Get general information on DAQ processor.

        Returns
        -------
        `pyxcp.types.GetDaqProcessorInfoResponse`
        """
        response = self.transport.request(types.Command.GET_DAQ_PROCESSOR_INFO)
        return types.GetDaqProcessorInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqResolutionInfo(self):
        """Get general information on DAQ processing resolution.

        Returns
        -------
        `pyxcp.types.GetDaqResolutionInfoResponse`
        """
        response = self.transport.request(types.Command.GET_DAQ_RESOLUTION_INFO)
        return types.GetDaqResolutionInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqListInfo(self, daqListNumber):
        """Get specific information for a DAQ list.

        Parameters
        ----------
        daqListNumber : int
        """
        dln = self.WORD_pack(daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqEventInfo(self, eventChannelNumber):
        """Get specific information for an event channel.

        Parameters
        ----------
        eventChannelNumber : int

        Returns
        -------
        `pyxcp.types.GetEventChannelInfoResponse`
        """
        ecn = self.WORD_pack(eventChannelNumber)
        response = self.transport.request(types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dtoCtrProperties(self, modifier, eventChannel, relatedEventChannel, mode):
        """DTO CTR properties

        Parameters
        ----------
        modifier :
        eventChannel : int
        relatedEventChannel : int
        mode :

        Returns
        -------
        `pyxcp.types.DtoCtrPropertiesResponse`
        """
        data = bytearray()
        data.append(modifier)
        data.extend(self.WORD_pack(eventChannel))
        data.extend(self.WORD_pack(relatedEventChannel))
        data.append(mode)
        response = self.transport.request(types.Command.DTO_CTR_PROPERTIES, *data)
        return types.DtoCtrPropertiesResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def setDaqPackedMode(self, daqListNumber, daqPackedMode, dpmTimestampMode=None, dpmSampleCount=None):
        """Set DAQ List Packed Mode.

        Parameters
        ----------
        daqListNumber : int
        daqPackedMode : int
        """
        params = []
        dln = self.WORD_pack(daqListNumber)
        params.extend(dln)
        params.append(daqPackedMode)

        if daqPackedMode == 1 or daqPackedMode == 2:
            params.append(dpmTimestampMode)
            dsc = self.WORD_pack(dpmSampleCount)
            params.extend(dsc)

        return self.transport.request(types.Command.SET_DAQ_PACKED_MODE, *params)

    @wrapped
    def getDaqPackedMode(self, daqListNumber):
        """Get DAQ List Packed Mode.

        This command returns information of the currently active packed mode of
        the addressed DAQ list.

        Parameters
        ----------
        daqListNumber : int
        """
        dln = self.WORD_pack(daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_PACKED_MODE, *dln)
        return types.GetDaqPackedModeResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    # dynamic
    @wrapped
    def freeDaq(self):
        """Clear dynamic DAQ configuration."""
        return self.transport.request(types.Command.FREE_DAQ)

    @wrapped
    def allocDaq(self, daqCount):
        """Allocate DAQ lists.

        Parameters
        ----------
        daqCount : int
            number of DAQ lists to be allocated
        """
        dq = self.WORD_pack(daqCount)
        return self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)

    @wrapped
    def allocOdt(self, daqListNumber, odtCount):
        dln = self.WORD_pack(daqListNumber)
        return self.transport.request(types.Command.ALLOC_ODT, 0, *dln, odtCount)

    @wrapped
    def allocOdtEntry(self, daqListNumber, odtNumber, odtEntriesCount):
        dln = self.WORD_pack(daqListNumber)
        return self.transport.request(types.Command.ALLOC_ODT_ENTRY, 0, *dln, odtNumber, odtEntriesCount)

    # PGM
    @wrapped
    def programStart(self):
        """Indicate the beginning of a programming sequence.

        Returns
        -------
        `pyxcp.types.ProgramStartResponse`
        """
        response = self.transport.request(types.Command.PROGRAM_START)
        return types.ProgramStartResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def programClear(self, mode: int, clearRange: int):
        """Clear a part of non-volatile memory.

        Parameters
        ----------
        mode : int
            0x00 = the absolute access mode is active (default)
            0x01 = the functional access mode is active
        clearRange : int
        """
        cr = self.DWORD_pack(clearRange)
        response = self.transport.request(types.Command.PROGRAM_CLEAR, mode, 0, 0, *cr)
        # ERR_ACCESS_LOCKED
        return response

    @wrapped
    def program(self, data: bytes):
        """"""
        d = bytearray()
        d.append(len(data))
        if self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            d.extend(b"\x00\x00")  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM, *d)

    @wrapped
    def programReset(self):
        """Indicate the end of a programming sequence."""
        return self.transport.request(types.Command.PROGRAM_RESET)

    @wrapped
    def getPgmProcessorInfo(self):
        """Get general information on PGM processor."""
        response = self.transport.request(types.Command.GET_PGM_PROCESSOR_INFO)
        return types.GetPgmProcessorInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getSectorInfo(self, mode, sectorNumber):
        """Get specific information for a sector."""
        response = self.transport.request(types.Command.GET_SECTOR_INFO, mode, sectorNumber)
        if mode == 0 or mode == 1:
            return types.GetSectorInfoResponseMode01.parse(response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 2:
            return types.GetSectorInfoResponseMode2.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def programPrepare(self, codesize):
        """Prepare non-volatile memory programming."""
        cs = self.WORD_pack(codesize)
        return self.transport.request(types.Command.PROGRAM_PREPARE, 0x00, *cs)

    @wrapped
    def programFormat(self, compressionMethod, encryptionMethod, programmingMethod, accessMethod):
        return self.transport.request(
            types.Command.PROGRAM_FORMAT, compressionMethod, encryptionMethod, programmingMethod, accessMethod
        )

    @wrapped
    def programNext(self, data):
        d = bytearray()
        d.append(len(data))
        if self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            d.extend(b"\x00\x00")  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM_NEXT, *d)

    @wrapped
    def programMax(self, data):
        d = bytearray()
        if self.slaveProperties.addressGranularity == types.AddressGranularity.WORD:
            d.extend(b"\x00")  # alignment bytes
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            d.extend(b"\x00\x00\x00")  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM_MAX, *d)

    @wrapped
    def programVerify(self, verMode, verType, verValue):
        data = bytearray()
        data.extend(self.WORD_pack(verType))
        data.extend(self.DWORD_pack(verValue))
        return self.transport.request(types.Command.PROGRAM_VERIFY, verMode, *data)

    # DBG

    @wrapped
    def dbgAttach(self):
        """Returns detailed information about the implemented version of the SW-DBG feature of the XCP slave

        Returns
        -------
        `pyxcp.types.DbgAttachResponse`
        """
        response = self.transport.request(types.Command.DBG_ATTACH)
        return types.DbgAttachResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgGetVendorInfo(self):
        """"""
        response = self.transport.request(types.Command.DBG_GET_VENDOR_INFO)
        return types.DbgGetVendorInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgGetModeInfo(self):
        """"""
        response = self.transport.request(types.Command.DBG_GET_MODE_INFO)
        return types.DbgGetModeInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgGetJtagId(self):
        """"""
        response = self.transport.request(types.Command.DBG_GET_JTAG_ID)
        return types.DbgGetJtagIdResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgHaltAfterReset(self):
        """"""
        return self.transport.request(types.Command.DBG_HALT_AFTER_RESET)

    @wrapped
    def dbgGetHwioInfo(self, index: int):
        """"""
        response = self.transport.request(types.Command.DBG_GET_HWIO_INFO, index)
        return types.DbgGetHwioInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgSetHwioEvent(self, index: int, trigger: int):
        """"""
        return self.transport.request(types.Command.DBG_SET_HWIO_EVENT, index, trigger)

    @wrapped
    def dbgHwioControl(self, pins):
        """"""
        d = bytearray()
        d.extend(self.BYTE_pack(len(pins)))
        for p in pins:
            d.extend(self.BYTE_pack(p[0]))  # index
            d.extend(self.BYTE_pack(p[1]))  # state
            d.extend(self.WORD_pack(p[2]))  # frequency

        response = self.transport.request(types.Command.DBG_HWIO_CONTROL, *d)
        return types.DbgHwioControlResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgExclusiveTargetAccess(self, mode: int, context: int):
        """"""
        return self.transport.request(types.Command.DBG_EXCLUSIVE_TARGET_ACCESS, mode, context)

    @wrapped
    def dbgSequenceMultiple(self, mode: int, num: int, *seq):
        """"""
        response = self.transport.request(types.Command.DBG_SEQUENCE_MULTIPLE, mode, self.WORD_pack(num), *seq)
        return types.DbgSequenceMultipleResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgLlt(self, num: int, mode: int, *llts):
        """"""
        response = self.transport.request(types.Command.DBG_LLT, num, mode, *llts)
        return types.DbgLltResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgReadModifyWrite(self, tri: int, width: int, address: int, mask: int, data: int):
        """"""
        d = bytearray()
        d.extend(b"\x00")
        d.append(tri)
        d.append(width)
        d.extend(b"\x00\x00")
        d.extend(self.DLONG_pack(address))
        if width == 0x01:
            d.extend(self.BYTE_pack(mask))
            d.extend(self.BYTE_pack(data))
        elif width == 0x02:
            d.extend(self.WORD_pack(mask))
            d.extend(self.WORD_pack(data))
        elif width == 0x04:
            d.extend(self.DWORD_pack(mask))
            d.extend(self.DWORD_pack(data))
        elif width == 0x08:
            d.extend(self.DLONG_pack(mask))
            d.extend(self.DLONG_pack(data))
        response = self.transport.request(types.Command.DBG_READ_MODIFY_WRITE, *d)
        return types.DbgReadModifyWriteResponse.parse(response, byteOrder=self.slaveProperties.byteOrder, width=width)

    @wrapped
    def dbgWrite(self, tri: int, width: int, address: int, data):
        """"""
        d = bytearray()
        d.extend(b"\x00")
        d.append(tri)
        self._dbg_width = width
        d.append(width)
        d.extend(self.WORD_pack(len(data)))
        d.extend(self.DLONG_pack(address))
        for da in data:
            if width == 0x01:
                d.extend(self.BYTE_pack(da))
            elif width == 0x02:
                d.extend(self.WORD_pack(da))
            elif width == 0x04:
                d.extend(self.DWORD_pack(da))
            elif width == 0x08:
                d.extend(self.DLONG_pack(da))
        return self.transport.request(types.Command.DBG_WRITE, *d)

    @wrapped
    def dbgWriteNext(self, num: int, data: int):
        """"""
        d = bytearray()
        d.extend(b"\x00")
        d.extend(self.WORD_pack(num))
        d.extend(b"\x00\x00")
        for i in range(num):
            if self._dbg_width == 0x01:
                d.extend(self.BYTE_pack(data[i]))
            elif self._dbg_width == 0x02:
                d.extend(self.WORD_pack(data[i]))
            elif self._dbg_width == 0x04:
                d.extend(self.DWORD_pack(data[i]))
            elif self._dbg_width == 0x08:
                d.extend(self.DLONG_pack(data[i]))
        return self.transport.request(types.Command.DBG_WRITE_NEXT, *d)

    @wrapped
    def dbgWriteCan1(self, tri: int, address: int):
        """"""
        d = bytearray()
        d.extend(self.BYTE_pack(tri))
        d.extend(self.DWORD_pack(address))
        return self.transport.request(types.Command.DBG_WRITE_CAN1, *d)

    @wrapped
    def dbgWriteCan2(self, width: int, num: int):
        """"""
        d = bytearray()
        self._dbg_width = width
        d.append(width)
        d.extend(self.BYTE_pack(num))
        return self.transport.request(types.Command.DBG_WRITE_CAN2, *d)

    @wrapped
    def dbgWriteCanNext(self, num: int, data: int):
        """"""
        d = bytearray()
        d.extend(self.BYTE_pack(num))
        for i in range(num):
            if self._dbg_width == 0x01:
                d.extend(self.BYTE_pack(data[i]))
            elif self._dbg_width == 0x02:
                d.extend(self.WORD_pack(data[i]))
            elif self._dbg_width == 0x04:
                d.extend(self.DWORD_pack(data[i]))
            elif self._dbg_width == 0x08:
                d.extend(self.DLONG_pack(data[i]))
        return self.transport.request(types.Command.DBG_WRITE_CAN_NEXT, *d)

    @wrapped
    def dbgRead(self, tri: int, width: int, num: int, address: int):
        """"""
        d = bytearray()
        d.extend(b"\x00")
        d.extend(self.BYTE_pack(tri))
        self._dbg_width = width
        d.extend(self.BYTE_pack(width))
        d.extend(self.WORD_pack(num))
        d.extend(self.DLONG_pack(address))
        response = self.transport.request(types.Command.DBG_READ, *d)
        return types.DbgReadResponse.parse(response, byteOrder=self.slaveProperties.byteOrder, width=width)

    @wrapped
    def dbgReadCan1(self, tri: int, address: int):
        """"""
        d = bytearray()
        d.extend(self.BYTE_pack(tri))
        d.extend(self.DWORD_pack(address))
        return self.transport.request(types.Command.DBG_READ_CAN1, *d)

    @wrapped
    def dbgReadCan2(self, width: int, num: int):
        """"""
        d = bytearray()
        self._dbg_width = width
        d.extend(self.BYTE_pack(width))
        d.extend(self.BYTE_pack(num))
        return self.transport.request(types.Command.DBG_READ_CAN2, *d)

    @wrapped
    def dbgGetTriDescTbl(self):
        """"""
        response = self.transport.request(types.Command.DBG_GET_TRI_DESC_TBL, b"\x00\x00\x00\x00\x00")
        return types.DbgGetTriDescTblResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dbgLlbt(self, data):
        """"""
        d = bytearray()
        d.extend(b"\x00")
        d.extend(self.WORD_pack(len(data)))
        for b in data:
            d.extend(self.BYTE_pack(b))
        response = self.transport.request(types.Command.DBG_LLBT, d)
        return types.DbgLlbtResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def timeCorrelationProperties(self, setProperties, getPropertiesRequest, clusterId):
        response = self.transport.request(
            types.Command.TIME_CORRELATION_PROPERTIES,
            setProperties,
            getPropertiesRequest,
            0,
            *self.WORD_pack(clusterId)
        )
        return types.TimeCorrelationPropertiesResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @broadcasted
    @wrapped
    def getSlaveID(self, mode: int):
        self.transportLayerCmd(0xFF, "X", "C", "P", mode)

    # Convenience Functions.
    def verify(self, addr, length):
        """Convenience function for verification of a data-transfer from slave
        to master (Not part of the XCP Specification).

        Parameters
        ----------
        addr : int
        length : int

        Returns
        -------
        bool
        """
        self.setMta(addr)
        cs = self.buildChecksum(length)
        self.logger.debug("BuildChecksum return'd: 0x{:08X} [{}]".format(cs.checksum, cs.checksumType))
        self.setMta(addr)
        data = self.fetch(length)
        cc = checksum.check(data, cs.checksumType)
        self.logger.debug("Our checksum          : 0x{:08X}".format(cc))
        return cs.checksum == cc

    def getDaqInfo(self):
        """Get DAQ information: processor, resolution, events."""
        result = {}
        dpi = self.getDaqProcessorInfo()
        processorInfo = {
            "minDaq": dpi["minDaq"],
            "maxDaq": dpi["maxDaq"],
            "properties": {
                "configType": dpi["daqProperties"]["daqConfigType"],
                "overloadEvent": dpi["daqProperties"]["overloadEvent"],
                "overloadMsb": dpi["daqProperties"]["overloadMsb"],
                "prescalerSupported": dpi["daqProperties"]["prescalerSupported"],
                "pidOffSupported": dpi["daqProperties"]["pidOffSupported"],
                "timestampSupported": dpi["daqProperties"]["timestampSupported"],
                "bitStimSupported": dpi["daqProperties"]["bitStimSupported"],
                "resumeSupported": dpi["daqProperties"]["resumeSupported"],
            },
            "keyByte": {
                "identificationField": dpi["daqKeyByte"]["Identification_Field"],
                "addressExtension": dpi["daqKeyByte"]["Address_Extension"],
                "optimisationType": dpi["daqKeyByte"]["Optimisation_Type"],
            },
        }
        result["processor"] = processorInfo

        dri = self.getDaqResolutionInfo()
        resolutionInfo = {
            "timestampTicks": dri["timestampTicks"],
            "maxOdtEntrySizeDaq": dri["maxOdtEntrySizeDaq"],
            "maxOdtEntrySizeStim": dri["maxOdtEntrySizeStim"],
            "granularityOdtEntrySizeDaq": dri["granularityOdtEntrySizeDaq"],
            "granularityOdtEntrySizeStim": dri["granularityOdtEntrySizeStim"],
            "timestampMode": {
                "unit": dri["timestampMode"]["unit"],
                "fixed": dri["timestampMode"]["fixed"],
                "size": dri["timestampMode"]["size"],
            },
        }
        result["resolution"] = resolutionInfo

        channels = []
        for ecn in range(dpi.maxEventChannel):
            eci = self.getDaqEventInfo(ecn)
            name = self.fetch(eci.eventChannelNameLength)
            channel = {
                "name": name.decode("latin-1"),
                "priority": eci["eventChannelPriority"],
                "unit": eci["eventChannelTimeUnit"],
                "cycle": eci["eventChannelTimeCycle"],
                "maxDaqList": eci["maxDaqList"],
                "properties": {
                    "consistency": eci["daqEventProperties"]["consistency"],
                    "daq": eci["daqEventProperties"]["daq"],
                    "stim": eci["daqEventProperties"]["stim"],
                    "packed": eci["daqEventProperties"]["packed"],
                },
            }
            channels.append(channel)
        result["channels"] = channels
        return result

    def getCurrentProtectionStatus(self):
        """"""
        if self.currentProtectionStatus is None:
            status = self.getStatus()
            self._setProtectionStatus(status.resourceProtectionStatus)
        return self.currentProtectionStatus

    def _setProtectionStatus(self, protection):
        """"""
        self.currentProtectionStatus = {
            "dbg": protection.dbg,
            "pgm": protection.pgm,
            "stim": protection.stim,
            "daq": protection.daq,
            "calpag": protection.calpag,
        }

    def cond_unlock(self, resources=None):
        """Conditionally unlock resources, i.e. only unlock locked resources.

        Precondition: Must assign :attr:`seedNKeyDLL`, e.g. ``master.seedNKeyDLL = "SeedNKeyXcp.dll"``

        Parameters
        ----------
        resources: str
            Comma or space separated list of resources, e.g. "DAQ, CALPAG".
            The names are not case-sensitive.
            Valid identifiers are: "calpag", "daq", "dbg", "pgm", "stim".

            If omitted, try to unlock every available resource.

        Raises
        ------
        ValueError
            Invalid resource name.

        `dllif.SeedNKeyError`
            In case of DLL related issues.
        """
        import re
        from pyxcp.dllif import getKey, SeedNKeyResult, SeedNKeyError

        MAX_PAYLOAD = self.slaveProperties["maxCto"] - 2

        if self._seedNKeyDLL is None:
            raise RuntimeError("No seed and key DLL specified, cannot proceed.")
        if resources is None:
            result = []
            if self.slaveProperties["supportsCalpag"]:
                result.append("calpag")
            if self.slaveProperties["supportsDaq"]:
                result.append("daq")
            if self.slaveProperties["supportsStim"]:
                result.append("stim")
            if self.slaveProperties["supportsPgm"]:
                result.append("pgm")
            resources = ",".join(result)
        protection_status = self.getCurrentProtectionStatus()
        resource_names = [r.lower() for r in re.split(r"[ ,]", resources) if r]
        for name in resource_names:
            if not name in types.RESOURCE_VALUES:
                raise ValueError("Invalid resource name '{}'.".format(name))
            if protection_status[name] == False:
                continue
            resource_value = types.RESOURCE_VALUES[name]
            result = self.getSeed(types.XcpGetSeedMode.FIRST_PART, resource_value)
            seed = list(result.seed)
            length = result.length
            if length == 0:
                continue
            if length > MAX_PAYLOAD:
                remaining = length - len(seed)
                while remaining > 0:
                    result = self.getSeed(types.XcpGetSeedMode.REMAINING, resource_value)
                    seed.extend(list(result.seed))
                    remaining = result.length
            result, key = getKey(self._seedNKeyDLL, resource_value, bytes(seed))
            if result == SeedNKeyResult.ACK:
                key = list(key)
                total_length = len(key)
                offset = 0
                while offset < total_length:
                    data = key[offset : offset + MAX_PAYLOAD]
                    key_length = len(data)
                    offset += key_length
                    res = self.unlock(key_length, data)
            else:
                raise SeedNKeyError("SeedAndKey DLL returned: {}".format(SeedNKeyResult(result).name))

    @property
    def seedNKeyDLL(self):
        return self._seedNKeyDLL

    @seedNKeyDLL.setter
    def seedNKeyDLL(self, name):
        self._seedNKeyDLL = name

def ticks_to_seconds(ticks, resolution):
    """Convert DAQ timestamp/tick value to seconds.

    Parameters
    ----------
    ticks: int

    unit: `GetDaqResolutionInfoResponse` as returned by :meth:`getDaqResolutionInfo`
    """
    warnings.warn("ticks_to_seconds() deprecated, use factory :func:`make_tick_converter` instead.", Warning)
    return (10 ** types.DAQ_TIMESTAMP_UNIT_TO_EXP[resolution.timestampMode.unit]) * resolution.timestampTicks * ticks

def make_tick_converter(resolution):
    """Make a function that converts tick count from XCP slave to seconds.

    Parameters
    ----------
    resolution: `GetDaqResolutionInfoResponse` as returned by :meth:`getDaqResolutionInfo`

    """
    exponent = types.DAQ_TIMESTAMP_UNIT_TO_EXP[resolution.timestampMode.unit]
    tick_resolution = resolution.timestampTicks
    base = (10 ** exponent) * tick_resolution

    def ticks_to_seconds(ticks):
        """Convert DAQ timestamp/tick value to seconds.

        Parameters
        ----------
        ticks: int

        Returns
        -------
        float
        """
        return base * ticks
    return ticks_to_seconds
