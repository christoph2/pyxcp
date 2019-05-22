#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Lowlevel API reflecting available XCP services.

.. note:: For technical reasons the API is split into two parts;
          common methods (this file) and a Python version specific part.

.. [1] XCP Specification, Part 2 - Protocol Layer Specification
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

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

from pyxcp import checksum
from pyxcp import types
from pyxcp.constants import (
    makeWordPacker, makeDWordPacker, makeWordUnpacker, makeDWordUnpacker)
from pyxcp.master.errorhandler import wrapped


class SlaveProperties(dict):
    """Container class for fixed parameters, like byte-order, maxCTO, ...
    """

    def __init__(self, *args, **kws):
        super(SlaveProperties, self).__init__(*args, **kws)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value


class MasterBaseType:
    """Common part of lowlevel XCP API.

    Parameters
    ----------
    transport : `pyxcp.transport.base` derived class.
        XCP transport layer, e.g. SxI, CAN, Ethernet
    loglevel : ["INFO", "WARN", "ERROR", "DEBUG"]
        to control logger output
    """
    def __init__(self, transport, loglevel="WARN"):
        self.ctr = 0
        self.succeeded = True
        self.logger = logging.getLogger("pyXCP")
        self.logger.setLevel(loglevel)
        self.transport = transport

        # In some cases the transport-layer needs to communicate with us.
        self.transport.parent = self
        self.service = None

        # (D)Word (un-)packers are byte-order dependent
        # -- byte-order is returned by CONNECT_Resp (COMM_MODE_BASIC)
        self.WORD_pack = None
        self.WORD_unpack = None
        self.DWORD_pack = None
        self.DWORD_unpack = None
        self.AG_pack = None
        self.AG_unpack = None

    def __enter__(self):
        """Context manager entry part.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit part.
        """
        self.close()
        if exc_type is None:
            return
        else:
            self.succeeded = False
            # print("=" * 79)
            # print("Exception while in Context-Manager:\n")
            self.logger.error(''.join(traceback.format_exception(
                exc_type, exc_val, exc_tb)))
            # print("=" * 79)
            # return True

    def _setService(self, service):
        """Records the currently processed service.

        Parameters
        ----------
        service: `pydbc.types.Command`

        Notes
        -----
        Internal Function, only to be used by transport-layer.
        """
        self.service = service

    def close(self):
        """Closes transport layer connection.
        """
        self.transport.close()

    # Mandatory Commands.
    @wrapped
    def connect(self):
        """Build up connection to an XCP slave.

        Before the actual XCP traffic starts a connection is required.

        Parameters
        ----------
        None

        Returns
        -------
        `pyxcp.types.ConnectResponse`
            Describes fundamental client properties.

        Note
        ----
        Every XCP slave supports at most one connection,
        more attempts to connect are silently ignored.

        """
        self.transport.connect()
        response = self.transport.request(types.Command.CONNECT, 0x00)

        # First get byte-order
        resultPartial = types.ConnectResponsePartial.parse(response)
        byteOrder = resultPartial.commModeBasic.byteOrder

        result = types.ConnectResponse.parse(response, byteOrder=byteOrder)
        self.slaveProperties = SlaveProperties(
            byteOrder=byteOrder, maxCto=result.maxCto, maxDto=result.maxDto)
        byteOrderPrefix = "<" if byteOrder == types.ByteOrder.INTEL else ">"

        self.slaveProperties.supportsPgm = result.resource.pgm
        self.slaveProperties.supportsStim = result.resource.stim
        self.slaveProperties.supportsDaq = result.resource.daq
        self.slaveProperties.supportsCalpag = result.resource.calpag
        self.slaveProperties.slaveBlockMode = \
            result.commModeBasic.slaveBlockMode
        self.slaveProperties.addressGranularity = \
            result.commModeBasic.addressGranularity
        self.slaveProperties.protocolLayerVersion = result.protocolLayerVersion
        self.slaveProperties.transportLayerVersion = \
            result.transportLayerVersion
        self.slaveProperties.optionalCommMode = \
            result.commModeBasic.optional

        self.WORD_pack = makeWordPacker(byteOrderPrefix)
        self.DWORD_pack = makeDWordPacker(byteOrderPrefix)
        self.WORD_unpack = makeWordUnpacker(byteOrderPrefix)
        self.DWORD_unpack = makeDWordUnpacker(byteOrderPrefix)

        if self.slaveProperties.addressGranularity == \
                types.AddressGranularity.BYTE:
            self.AG_pack = struct.Struct("<B").pack
            self.AG_unpack = struct.Struct("<B").pack
        elif self.slaveProperties.addressGranularity == \
                types.AddressGranularity.WORD:
            self.AG_pack = self.WORD_pack
            self.AG_unpack = self.WORD_unpack
        elif self.slaveProperties.addressGranularity == \
                types.AddressGranularity.DWORD:
            self.AG_pack = self.DWORD_pack
            self.AG_unpack = self.DWORD_unpack

        return result

    @wrapped
    def disconnect(self):
        """Releases the connection to the XCP slave.

        Thereafter, no further communication with the slave is possible
        (besides `connect`).

        Parameters
        ----------
        None

        Returns
        -------
        None

        Notes
        -----
        If DISCONNECT is currently not possible, ERR_CMD_BUSY will be returned.
        """
        response = self.transport.request(types.Command.DISCONNECT)
        return response

    @wrapped
    def getStatus(self):
        """Get current status information of the slave device.

        This includes the status of the resource protection, pending store
        requests and the general status of data acquisition and stimulation.

        Returns
        -------
        `types.GetStatusResponse`
        """
        response = self.transport.request(types.Command.GET_STATUS)
        result = types.GetStatusResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        return result

    @wrapped
    def synch(self):
        """Synchronize command execution after timeout conditions.

        """
        response = self.transport.request(types.Command.SYNCH)
        return response

    @wrapped
    def getCommModeInfo(self):
        """Get optional information on different Communication Modes supported
        by the slave.

        Returns
        -------
        `pyxcp.types.GetCommModeInfoResponse`
        """
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)
        result = types.GetCommModeInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.interleavedMode = result.commModeOptional.interleavedMode
        self.slaveProperties.masterBlockMode = result.commModeOptional.masterBlockMode
        self.slaveProperties.maxBs = result.maxBs
        self.slaveProperties.minSt = result.minSt
        self.slaveProperties.queueSize = result.queueSize
        self.slaveProperties.xcpDriverVersionNumber = result.xcpDriverVersionNumber
        return result

    @wrapped
    def getId(self, mode):
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

            `types.XcpGetIdType`may be used.

        Returns
        -------
        `pydbc.types.GetIDResponse`
        """
        response = self.transport.request(types.Command.GET_ID, mode)
        result = types.GetIDResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        result.length = self.DWORD_unpack(response[3:7])[0]
        return result

    @wrapped
    def setRequest(self, mode, sessionConfigurationId):
        """Request to save to non-volatile memory.

        Parameters
        ----------
        mode : int (bitfield)
            - 1  Request to store cALibration data
            - 2  Request to store DAQ list, no resume
            - 4  Request to store DAQ list, resume enabled
            - 8  Request to clear DAQ configuration
        sessionConfigurationId : int

        Returns
        -------
        T.B.D
        """
        response = self.transport.request(
            types.Command.SET_REQUEST, mode,
            sessionConfigurationId >> 8, sessionConfigurationId & 0xff)
        return response

    @wrapped
    def getSeed(self, first, resource):
        """Get seed from slave for unlocking a protected resource.

        Parameters
        ----------
        first : int
            0 - first part of seed
            1 - remaining part
        resource : int
            Mode==0 - Resource
            Mode==1 - Don’t care

        Returns
        -------
        TODO: `pydbc.types.GetSeedResponse`
        """
        response = self.transport.request(
            types.Command.GET_SEED, first, resource)
        return types.GetSeedResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def unlock(self, length, key):
        """Send key to slave for unlocking a protected resource.

        Parameters
        ----------
        length : int
            indicates the (remaining) number of key bytes.
        key : bytes

        Returns
        -------
        `pydbc.types.ResourceType`

        .. note:: The master has to use `unlock` in a defined sequence together
                  with `getSeed`. The master only can send an `unlock` sequence
                  if previously there was a `getSeed` sequence. The master has
                  to send the first `unlocking` after a `getSeed` sequence with
                  a Length containing the total length of the key.
        """
        response = self.transport.request(types.Command.UNLOCK, length, *key)
        return types.ResourceType.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def setMta(self, address, addressExt=0x00):
        """Set Memory Transfer Address in slave.

        Parameters
        ----------
        address : int
        addressExt : int

        .. note:: The MTA is used by `buildChecksum`, `upload`, `download`,
                  `downloadNext`, `downloadMax`, `modifyBits`, `programClear`,
                  `program`, `programNext` and `programMax`.
        """
        addr = self.DWORD_pack(address)
        response = self.transport.request(
            types.Command.SET_MTA, 0, 0, addressExt, *addr)
        return response

    @wrapped
    def upload(self, length):
        """Transfer data from slave to master.

        Parameters
        ----------
        length : int

        .. note:: Adress is set via `setMta` (Some services like `getID` also
        set the MTA).

        Returns
        -------
        bytes
        """

        response = self.transport.request(types.Command.UPLOAD, length)
        if length > self.transport.MAX_DATAGRAM_SIZE:
            block_response = self.transport.block_receive(
                length_required=(length - len(response)))
            response += block_response
        return response

    @wrapped
    def shortUpload(self, length, address, addressExt=0x00):
        """Transfer data from slave to master.
        As opposed to `upload` this service includes address information.

        Parameters
        ----------
        address : int
        addressExt : int

        Returns
        -------
        bytes
        """
        addr = self.DWORD_pack(address)
        response = self.transport.request(
            types.Command.SHORT_UPLOAD, length, 0, addressExt, *addr)
        return response

    @wrapped
    def buildChecksum(self, blocksize):
        """Build checksum over memory range.

        Parameters
        ----------
        blocksize : int

        Returns
        -------
        `pyxcp.types.BuildChecksumResponse`

        .. note:: Adress is set via `setMta`

        See Also
        --------
        Module `pyxcp.checksum`
        """
        bs = self.DWORD_pack(blocksize)
        response = self.transport.request(
            types.Command.BUILD_CHECKSUM, 0, 0, 0, *bs)
        return types.BuildChecksumResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def transportLayerCmd(self, subCommand, *data):
        """Execute transfer-layer specific command.

        Parameters
        ----------
        subCommand : int
        data : bytes

        Returns
        -------
        Dependent on command

        .. note:: For details refer to XCP specification.
        """
        response = self.transport.request(
            types.Command.TRANSPORT_LAYER_CMD, subCommand, *data)
        return response

    @wrapped
    def userCmd(self, subCommand, *data):
        """Execute proprietary command implemented in your XCP client.

        Parameters
        ----------
        subCommand : int
        data : bytes

        Returns
        -------
        Dependent on command

        .. note:: For details refer to your XCP client vendor.
        """

        response = self.transport.request(
            types.Command.USER_CMD, subCommand, *data)
        return response

    @wrapped
    def getVersion(self):
        """Get version information.

        This command returns detailed information about the implemented
        protocol layer version of the XCP slave and the transport layer
        currently in use.

        Returns
        -------
        `types.GetVersionResponse`
        """

        response = self.transport.request(types.Command.GET_VERSION)
        result = types.GetVersionResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.protocolMajor = result.protocolMajor
        self.slaveProperties.protocolMinor = result.protocolMinor
        self.slaveProperties.transportMajor = result.transportMajor
        self.slaveProperties.transportMinor = result.transportMinor
        return result

    def fetch(self, length, limitPayload=None):  # TODO: pull
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

        .. note:: address information is not included because of services like
                  `getID`.
        """
        if limitPayload and limitPayload < 8:
            raise ValueError(
                "Payload must be at least 8 bytes - given: {}".format(
                    limitPayload))
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

    # Calibration Commands (CAL)
    @wrapped
    def download(self, *data):
        """Transfer data from master to slave.

        Parameters
        ----------
        data : bytes

        .. note:: Adress is set via `setMta`
        """

        length = len(data)
        response = self.transport.request(
            types.Command.DOWNLOAD, length, *data)
        return response

    @wrapped
    def downloadNext(self, *data):
        """Transfer data from master to slave (block mode).

        Parameters
        ----------
        data : bytes
        """

        length = len(data)
        response = self.transport.request(
            types.Command.DOWNLOAD_NEXT, length, *data)
        return response

    @wrapped
    def downloadMax(self, *data):
        """Transfer data from master to slave (fixed size).

        Parameters
        ----------
        data : bytes
        """
        response = self.transport.request(types.Command.DOWNLOAD_MAX, *data)
        return response

    # Page Switching Commands (PAG)
    @wrapped
    def setCalPage(self, mode, logicalDataSegment, logicalDataPage):
        """Set calibration page.

        Parameters
        ----------
        mode : int (bitfield)
            0x01 - The given page will be used by the slave device application.
            0x02 - The slave device XCP driver will access the given page.
            0x80 - The logical segment number is ignored. The command applies
                   to all segments
        logicalDataSegment : int
        logicalDataPage : int
        """
        response = self.transport.request(
            types.Command.SET_CAL_PAGE, mode, logicalDataSegment,
            logicalDataPage)
        return response

    @wrapped
    def getCalPage(self, mode, logicalDataSegment):
        """Get calibration page

        Parameters
        ----------
        mode : int
        logicalDataSegment : int
        """
        response = self.transport.request(
            types.Command.GET_CAL_PAGE, mode, logicalDataSegment)
        return response[2]

    @wrapped
    def getPagProcessorInfo(self):
        """Get general information on PAG processor.

        Returns
        -------
        `pydbc.types.GetPagProcessorInfoResponse`
    """
        response = self.transport.request(types.Command.GET_PAG_PROCESSOR_INFO)
        return types.GetPagProcessorInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getSegmentInfo(self, mode, segmentNumber, segmentInfo, mappingIndex):
        """Get specific information for a segment.

        Parameters
        ----------
        mode : int
            0 = get basic address info for this segment
            1 = get standard info for this segment
            2 = get address mapping info for this segment
        segmentNumber : int
        segmentInfo : int
            Mode 0:
                0 = address
                1 = length
            Mode 1: don’t care
            Mode 2:
                0 = source address
                1 = destination address
                2 = length address
        mappingIndex : int
            Mode 0: don’t care
            Mode 1: don’t care
            Mode 2: identifier for address mapping range that mapping_info
                    belongs to.

        """
        response = self.transport.request(
            types.Command.GET_SEGMENT_INFO, mode, segmentNumber, segmentInfo,
            mappingIndex)
        if mode == 0:
            return types.GetSegmentInfoMode0Response.parse(
                response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 1:
            return types.GetSegmentInfoMode1Response.parse(
                response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 2:
            return types.GetSegmentInfoMode2Response.parse(
                response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getPageInfo(self, segmentNumber, pageNumber):
        """Get specific information for a page.

        Parameters
        ----------
        segmentNumber : int
        pageNumber : int
        """
        response = self.transport.request(
            types.Command.GET_PAGE_INFO, 0, segmentNumber, pageNumber)
        return (types.PageProperties.parse(
            bytes([response[0]]),
            byteOrder=self.slaveProperties.byteOrder),
            response[1])

    @wrapped
    def setSegmentMode(self, mode, segmentNumber):
        """Set mode for a segment.

        Parameters
        ----------
        mode : int (bitfield)
            1 = enable FREEZE Mode
        segmentNumber : int
        """
        response = self.transport.request(
            types.Command.SET_SEGMENT_MODE, mode, segmentNumber)
        return response

    @wrapped
    def getSegmentMode(self, segmentNumber):
        """Get mode for a segment.

        Parameters
        ----------
        segmentNumber : int
        """
        response = self.transport.request(
            types.Command.GET_SEGMENT_MODE, 0, segmentNumber)
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
        response = self.transport.request(
            types.Command.COPY_CAL_PAGE, srcSegment, srcPage, dstSegment,
            dstPage)
        return response

    # DAQ
    @wrapped
    def clearDaqList(self, daqListNumber):
        """Clear DAQ list configuration.

        Parameters
        ----------
        daqListNumber : int
        """
        daqList = self.WORD_pack(daqListNumber)
        response = self.transport.request(
            types.Command.CLEAR_DAQ_LIST, 0, *daqList)
        return response

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
        response = self.transport.request(
            types.Command.WRITE_DAQ, bitOffset, entrySize, addressExt, *addr)
        return response

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
        response = self.transport.request(
            types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

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
        response = self.transport.request(
            types.Command.START_STOP_DAQ_LIST, mode, *dln)
        return types.StartStopDaqListResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

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
        response = self.transport.request(types.Command.START_STOP_SYNCH, mode)
        return response

    @wrapped
    def writeDaqMultiple(self, daqElements):
        """Write multiple elements in ODT.

        Parameters
        ----------
        daqElements : list of DAQ elements
        """

        data = bytearray()
        data.append(len(daqElements))

        for daqElement in daqElements:
            data.extend(types.DaqElement.build(
                daqElement,
                byteOrder=self.slaveProperties.byteOrder))

        response = self.transport.request(
            types.Command.WRITE_DAQ_MULTIPLE, *data)
        return response

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
        result = types.GetDaqClockResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        return result.timestamp

    @wrapped
    def readDaq(self):
        """Read element from ODT entry.

        Returns
        -------
        `pyxcp.types.ReadDaqResponse`
        """
        response = self.transport.request(types.Command.READ_DAQ)
        return types.ReadDaqResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqProcessorInfo(self):
        """Get general information on DAQ processor.

        Returns
        -------
        `pyxcp.types.GetDaqProcessorInfoResponse`
        """
        response = self.transport.request(types.Command.GET_DAQ_PROCESSOR_INFO)
        return types.GetDaqProcessorInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqResolutionInfo(self):
        """Get general information on DAQ processing resolution.

        Returns
        -------
        `pyxcp.types.GetDaqResolutionInfoResponse`
        """
        response = self.transport.request(
            types.Command.GET_DAQ_RESOLUTION_INFO)
        return types.GetDaqResolutionInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqListInfo(self, daqListNumber):
        """Get specific information for a DAQ list.

        Parameters
        ----------
        daqListNumber : int
        """
        dln = self.WORD_pack(daqListNumber)
        response = self.transport.request(
            types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

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
        response = self.transport.request(
            types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dtoCtrProperties(
            self, modifier, eventChannel, relatedEventChannel, mode):
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
        response = self.transport.request(
            types.Command.DTO_CTR_PROPERTIES, *data)
        return types.DtoCtrPropertiesResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def setDaqPackedMode(
            self, daqListNumber, daqPackedMode,
            dpmTimestampMode=None, dpmSampleCount=None):
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

        response = self.transport.request(
            types.Command.SET_DAQ_PACKED_MODE,
            *params)
        return response

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
        response = self.transport.request(
            types.Command.GET_DAQ_PACKED_MODE, *dln)
        result = types.GetDaqPackedModeResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)
        return result

    # dynamic
    @wrapped
    def freeDaq(self):
        """Clear dynamic DAQ configuration.
        """
        response = self.transport.request(types.Command.FREE_DAQ)
        return response

    @wrapped
    def allocDaq(self, daqCount):
        """Allocate DAQ lists.

        Parameters
        ----------
        daqCount : int
            number of DAQ lists to be allocated
        """
        dq = self.WORD_pack(daqCount)
        response = self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)
        return response

    # PGM
    @wrapped
    def programStart(self):
        """Indicate the beginning of a programming sequence.

        Returns
        -------
        `pyxcp.types.ProgramStartResponse`
        """
        response = self.transport.request(types.Command.PROGRAM_START)
        return types.ProgramStartResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def programClear(self, mode, clearRange):
        """Clear a part of non-volatile memory.

        Parameters
        ----------
        mode : int
            0x00 = the absolute access mode is active (default)
            0x01 = the functional access mode is active
        clearRange : int
        """
        cr = self.DWORD_pack(clearRange)
        response = self.transport.request(
            types.Command.PROGRAM_CLEAR, mode, 0, 0, *cr)
        # ERR_ACCESS_LOCKED
        return response

    @wrapped
    def program(self, data):
        """
        PROGRAM
        Position Type Description
        0 BYTE Command Code = 0xD0
        1 BYTE Number of data elements [AG] [1..(MAX_CTO-2)/AG]
        2..AG-1 BYTE Used for alignment, only if AG >2
            AG=1: 2..MAX_CTO-2
            AG>1: AG MAX_CTO-AG
        ELEMENT Data elements
        """
        d = bytearray()
        d.append(len(data))
        if self.slaveProperties.addressGranularity == \
                types.AddressGranularity.DWORD:
            d.extend(b'\x00\x00')  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM, *d)

    def programReset(self):
        """Indicate the end of a programming sequence."""
        return self.transport.request(types.Command.PROGRAM_RESET)

    def getPgmProcessorInfo(self):
        """Get general information on PGM processor."""
        response = self.transport.request(types.Command.GET_PGM_PROCESSOR_INFO)
        return types.GetPgmProcessorInfoResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

    def getSectorInfo(self, mode, sectorNumber):
        """Get specific information for a sector."""
        response = self.transport.request(
            types.Command.GET_SECTOR_INFO, mode, sectorNumber)
        if mode == 0 or mode == 1:
            return types.GetSectorInfoResponseMode01.parse(
                response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 2:
            return types.GetSectorInfoResponseMode2.parse(
                response, byteOrder=self.slaveProperties.byteOrder)

    def programPrepare(self, codesize):
        """Prepare non-volatile memory programming."""
        cs = self.WORD_pack(codesize)
        return self.transport.request(types.Command.PROGRAM_PREPARE, 0x00, *cs)

    def programFormat(
            self, compressionMethod, encryptionMethod, programmingMethod,
            accessMethod):
        return self.transport.request(
            types.Command.PROGRAM_FORMAT, compressionMethod, encryptionMethod,
            programmingMethod, accessMethod)

    def programNext(self, data):
        d = bytearray()
        d.append(len(data))
        if self.slaveProperties.addressGranularity == \
                types.AddressGranularity.DWORD:
            d.extend(b'\x00\x00')  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM_NEXT, *d)

    def programMax(self, data):
        d = bytearray()
        if self.slaveProperties.addressGranularity == \
                types.AddressGranularity.WORD:
            d.extend(b'\x00')  # alignment bytes
        elif self.slaveProperties.addressGranularity == \
                types.AddressGranularity.DWORD:
            d.extend(b'\x00\x00\x00')  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM_MAX, *d)

    def programVerify(self, verMode, verType, verValue):
        data = bytearray()
        data.extend(self.WORD_pack(verType))
        data.extend(self.DWORD_pack(verValue))
        return self.transport.request(
            types.Command.PROGRAM_VERIFY, verMode, *data)

    def timeCorrelationProperties(
            self, setProperties, getPropertiesRequest, clusterId):
        response = self.transport.request(
            types.Command.TIME_CORRELATION_PROPERTIES,
            setProperties, getPropertiesRequest, 0, *self.WORD_pack(clusterId))
        return types.TimeCorrelationPropertiesResponse.parse(
            response, byteOrder=self.slaveProperties.byteOrder)

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
        self.logger.debug("BuildChecksum return'd: 0x{:08X} [{}]".format(
            cs.checksum, cs.checksumType))
        self.setMta(addr)
        data = self.fetch(length)
        cc = checksum.check(data, cs.checksumType)
        self.logger.debug("Our checksum          : 0x{:08X}".format(cc))
        return cs.checksum == cc
