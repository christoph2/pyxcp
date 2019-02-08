#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__="""
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2018 by Christoph Schueler <cpu12.gems@googlemail.com>

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

import enum
import logging
import struct
import traceback

from pyxcp import checksum
from pyxcp import types


class MasterBaseType(object):

    def __init__(self, transport):
        self.ctr = 0
        self.succeeded = True
        self.logger = logging.getLogger("pyXCP")
        self.transport = transport

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type is None:
            return
        else:
            self.succeeded = False
            #print("=" * 79)
            #print("Exception while in Context-Manager:\n")
            self.logger.error(''.join(traceback.format_exception(exc_type, exc_val, exc_tb)))
            #print("=" * 79)
        return True

    def close(self):
        self.transport.close()

    ##
    ## Mandatory Commands.
    ##
    def connect(self):
        """Build up connection to an XCP slave.

        Before the actual XCP traffic starts a connection is required.

        Parameters
        ----------
        None

        Returns
        -------
        `types.ConnectResponse`
            Describes fundamental client properties.

        Note
        ----
        Every XCP slave supports at most one connection,
        more attempts to connect are silently ignored.

        """
        response = self.transport.request(types.Command.CONNECT, 0x00)
        result = types.ConnectResponse.parse(response)
        self.maxCto = result.maxCto
        self.maxDto = result.maxDto

        self.supportsPgm = result.resource.pgm
        self.supportsStim = result.resource.stim
        self.supportsDaq = result.resource.daq
        self.supportsCalpag = result.resource.calpag
        return result

    def disconnect(self):
        """Releases the connection to the XCP slave.

        Thereafter, no further communication with the slave is possible (besides `connect`).

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

    def getStatus(self):
        """Get current status information of the slave device.

        This includes the status of the resource protection, pending store requests and the general
        status of data acquisition and stimulation.

        Returns
        -------
        `types.GetStatusResponse`
        """
        response = self.transport.request(types.Command.GET_STATUS)
        result = types.GetStatusResponse.parse(response)
        return result

    def synch(self):
        """Synchronize command execution after timeout conditions.

        """
        response = self.transport.request(types.Command.SYNCH)
        return response

    def getCommModeInfo(self):
        """Get optional information on different Communication Modes supported by the slave.

        Returns
        -------
        `types.GetCommModeInfoResponse`
        """
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)
        result = types.GetCommModeInfoResponse.parse(response)
        return result

    def getID(self, mode):
        """This command is used for automatic session configuration and for slave device identification.

        Parameters
        ----------
        mode: uint8
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
        `types.GetIDResponse`
        """
        response = self.transport.request(types.Command.GET_ID, mode)
        result = types.GetIDResponse.parse(response)
        result.length = struct.unpack("<I", response[3 : 7])[0]
        return result

    def setRequest(self, mode, sessionConfigurationId):
        """Request to save to non-volatile memory.

        Parameters
        ----------
        mode: uint8
            tbd
        sessionConfigurationId: uint16
            tbd
        """
        response = self.transport.request(types.Command.SET_REQUEST, mode, sessionConfigurationId >> 8, sessionConfigurationId & 0xff)
        return response

    def upload(self, length):
        response = self.transport.request(types.Command.UPLOAD, length)
        return response

    def shortUpload(self, length):
        response = self.transport.request(types.Command.SHORT_UPLOAD, length)
        return response[1 : ]

    def setMta(self, address):
        addr = struct.pack("<I", address)
        response = self.transport.request(types.Command.SET_MTA, 0, 0, 0, *addr)
        return response

    def getSeed(self, first, resource):
        response = self.transport.request(types.Command.GET_SEED, first, resource)
        return response[1], response[1 : ]

    def unlock(self, length, key):
        response = self.transport.request(types.Command.UNLOCK, length, *key)
        return types.ResourceType.parse(response)

    def fetch(self, length, limitPayload = None): ## TODO: pull
        if limitPayload and limitPayload < 8:
            raise ValueError("Payload must be at least 8 bytes - given: {}".format(limitPayload))
        maxPayload = self.maxCto - 1
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

    def buildChecksum(self, blocksize):
        bs = struct.pack("<I", blocksize)
        response = self.transport.request(types.Command.BUILD_CHECKSUM, 0, 0, 0, *bs)
        return types.BuildChecksumResponse.parse(response)

    def transportLayerCommand(self, subCommand, *data):
        response = self.transport.request(types.Command.TRANSPORT_LAYER_CMD, subCommand, *data)
        return response

    def userCommand(self, subCommand, *data):
        response = self.transport.request(types.Command.USER_CMD, subCommand, *data)
        return response

    ##
    ## Calibration Commands (CAL)
    ##
    def download(self, *data):
        length = len(data)
        response = self.transport.request(types.Command.DOWNLOAD, length, *data)
        return response

    def downloadNext(self, *data):
        length = len(data)
        response = self.transport.request(types.Command.DOWNLOAD_NEXT, length, *data)
        return response

    def downloadMax(self, *data):
        response = self.transport.request(types.Command.DOWNLOAD_MAX, *data)
        return response

    ##
    ## Page Switching Commands (PAG)
    ##
    def setCalPage(self, mode, logicalDataSegment, logicalDataPage):
        response = self.transport.request(types.Command.SET_CAL_PAGE, mode, logicalDataSegment, logicalDataPage)
        return response

    def getCalPage(self, mode, logicalDataSegment):
        response = self.transport.request(types.Command.GET_CAL_PAGE, mode, logicalDataSegment)
        return response

    def getPagProcessorInfo(self):
        response = self.transport.request(types.Command.GET_PAG_PROCESSOR_INFO)
        return types.GetPagProcessorInfoResponse.parse(response)

    def getSegmentInfo(self, mode, segmentNumber, segmentInfo, mappingIndex):
        response = self.transport.request(types.Command.GET_SEGMENT_INFO, mode, segmentNumber, segmentInfo, mappingIndex)
        if mode == 0:
            return types.GetSegmentInfoMode0Response.parse(response)
        elif mode == 1:
            return types.GetSegmentInfoMode1Response.parse(response)
        elif mode == 2:
            return types.GetSegmentInfoMode2Response.parse(response)

    def getPageInfo(self, segmentNumber, pageNumber):
        response = self.transport.request(types.Command.GET_PAGE_INFO, 0, pageNumber)
        return (types.PageProperties.parse(response[1]), response[2])

    def setSegmentMode(self, mode, segmentNumber):
        response = self.transport.request(types.Command.SET_SEGMENT_MODE, mode, segmentNumber)
        return response

    def getSegmentMode(self, segmentNumber):
        response = self.transport.request(types.Command.GET_SEGMENT_MODE, 0, segmentNumber)
        return response[2]

    def copyCalPage(self, srcSegment, srcPage, dstSegment, dstPage):
        response = self.transport.request(types.Command.COPY_CAL_PAGE, srcSegment, srcPage, dstSegment, dstPage)
        return response

    ##
    ## DAQ
    ##
    def clearDaqList(self, daqListNumber):
        daqList = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.CLEAR_DAQ_LIST, 0, *daqList)
        return response

    def writeDaq(self, bitOffset, entrySize, addressExt, address):
        addr = struct.pack("<I", address)
        response = self.transport.request(types.Command.WRITE_DAQ, bitOffset, entrySize, addressExt, *addr)
        return response

    def getDaqListMode(self, daqListNumber):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(response)

    def startStopDaqList(self, mode, daqListNumber):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.START_STOP_DAQ_LIST, mode, *dln)
        return response

    def startStopSynch(self, mode):
        response = self.transport.request(types.Command.START_STOP_SYNCH, mode)
        return response

    ## optional.
    def getDaqClock(self):
        response = self.transport.request(types.Command.GET_DAQ_CLOCK)
        result = types.GetDaqClockResponse.parse(response)
        return result.timestamp

    def readDaq(self):
        response = self.transport.request(types.Command.READ_DAQ)
        return types.ReadDaqResponse.parse(response)

    def getDaqProcessorInfo(self):
        response = self.transport.request(types.Command.GET_DAQ_PROCESSOR_INFO)
        return types.GetDaqProcessorInfoResponse.parse(response)

    def getDaqResolutionInfo(self):
        response = self.transport.request(types.Command.GET_DAQ_RESOLUTION_INFO)
        return types.GetDaqResolutionInfoResponse.parse(response)

    def getDaqListInfo(self, daqListNumber):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(response)

    def getEventChannelInfo(self, eventChannelNumber):
        ecn = struct.pack("<H", eventChannelNumber)
        response = self.transport.request(types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(response)

    # dynamic
    def freeDaq(self):
        response = self.transport.request(types.Command.FREE_DAQ)
        return response

    def allocDaq(self, daqCount):
        dq = struct.pack("<H", daqCount)
        response = self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)
        return response

    ##
    ## PGM
    ##
    def programStart(self):
        response = self.transport.request(types.Command.PROGRAM_START)
        return types.ProgramStartResponse.parse(response)

    def programClear(self, mode, clearRange):
        cr = struct.pack("<I", clearRange)
        response = self.transport.request(types.Command.PROGRAM_CLEAR, mode, 0, 0, *cr)
        # ERR_ACCESS_LOCKED
        return response

    def program(self):
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

