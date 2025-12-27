#!/usr/bin/env python
"""Lowlevel API reflecting available XCP services.

.. note:: For technical reasons the API is split into two parts;
          common methods (this file) and a Python version specific part.

.. [1] XCP Specification, Part 2 - Protocol Layer Specification
"""

import functools
import logging
import struct
import traceback
import warnings
from contextlib import suppress
from typing import Any, Callable, Collection, Dict, Optional, TypeVar

from pyxcp.daq_stim.stim import DaqEventInfo, Stim

from pyxcp import checksum, types
from pyxcp.constants import (
    makeBytePacker,
    makeByteUnpacker,
    makeDLongPacker,
    makeDLongUnpacker,
    makeDWordPacker,
    makeDWordUnpacker,
    makeWordPacker,
    makeWordUnpacker,
)
from pyxcp.master.errorhandler import (
    SystemExit,
    disable_error_handling,
    is_suppress_xcp_error_log,
    set_suppress_xcp_error_log,
    wrapped,
)
from pyxcp.transport.base import create_transport
from pyxcp.utils import decode_bytes, delay, short_sleep

# Type variables for better type hinting
T = TypeVar("T")
R = TypeVar("R")


def broadcasted(func: Callable):
    """"""
    return func


class SlaveProperties(dict):
    """Container class for fixed parameters, like byte-order, maxCTO, ...

    This class extends dict to provide attribute-style access to dictionary items.
    """

    def __init__(self, *args: Any, **kws: Any) -> None:
        """Initialize a new SlaveProperties instance.

        Parameters
        ----------
        *args : Any
            Positional arguments passed to dict.__init__
        **kws : Any
            Keyword arguments passed to dict.__init__
        """
        super().__init__(*args, **kws)

    def __getattr__(self, name: str) -> Any:
        """Get an attribute by name.

        Parameters
        ----------
        name : str
            The name of the attribute to get

        Returns
        -------
        Any
            The value of the attribute
        """
        return self[name]

    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute by name.

        Parameters
        ----------
        name : str
            The name of the attribute to set
        value : Any
            The value to set
        """
        self[name] = value

    def __getstate__(self) -> dict:
        """Get the state of the object for pickling.

        Returns
        -------
        dict
            The state of the object
        """
        return self

    def __setstate__(self, state: dict) -> None:
        """Set the state of the object from unpickling.

        Parameters
        ----------
        state : dict
            The state to set
        """
        self.update(state)  # Use update instead of direct assignment


class Master:
    """Common part of lowlevel XCP API.

    This class provides methods for interacting with an XCP slave device.
    It handles the communication protocol and provides a high-level API
    for sending commands and receiving responses.

    Parameters
    ----------
    transport_name : str | None
        XCP transport layer name ['can', 'eth', 'sxi']
    config : Any
        Configuration object containing transport and general settings
    policy : Any, optional
        Policy object for handling frames, by default None
    transport_layer_interface : Any, optional
        Custom transport layer interface, by default None
    """

    def __init__(self, transport_name: str | None, config: Any, policy: Any = None,
                 transport_layer_interface: Any = None) -> None:
        """Initialize a new Master instance.

        Parameters
        ----------
        transport_name : str | None
            XCP transport layer name ['can', 'eth', 'sxi']
        config : Any
            Configuration object containing transport and general settings
        policy : Any, optional
            Policy object for handling frames, by default None
        transport_layer_interface : Any, optional
            Custom transport layer interface, by default None

        Raises
        ------
        ValueError
            If transport_name is None
        """
        if transport_name is None:
            raise ValueError("No transport-layer selected")  # Never reached -- to keep type-checkers happy.

        # Initialize basic properties
        self.ctr: int = 0
        self.succeeded: bool = True
        self.config: Any = config.general
        self.logger: logging.Logger = logging.getLogger("PyXCP")

        # Configure error handling
        disable_error_handling(self.config.disable_error_handling)

        # Set up transport layer
        self.transport_name: str = transport_name.lower()
        transport_config: Any = config.transport
        self.transport: BaseTransport = create_transport(transport_name, transport_config, policy,
                                                         transport_layer_interface)

        # Set up STIM (stimulation) support
        self.stim: Stim = Stim(self.config.stim_support)
        self.stim.clear()
        self.stim.set_policy_feeder(self.transport.policy.feed)
        self.stim.set_frame_sender(self.transport.block_request)

        # In some cases the transport-layer needs to communicate with us.
        self.transport.parent = self
        self.service: Any = None

        # Policies may issue XCP commands on their own.
        self.transport.policy.xcp_master = self

        # (D)Word (un-)packers are byte-order dependent
        # -- byte-order is returned by CONNECT_Resp (COMM_MODE_BASIC)
        self.BYTE_pack: Callable[[int], bytes] | None = None
        self.BYTE_unpack: Callable[[bytes], tuple[int]] | None = None
        self.WORD_pack: Callable[[int], bytes] | None = None
        self.WORD_unpack: Callable[[bytes], tuple[int]] | None = None
        self.DWORD_pack: Callable[[int], bytes] | None = None
        self.DWORD_unpack: Callable[[bytes], tuple[int]] | None = None
        self.DLONG_pack: Callable[[int], bytes] | None = None
        self.DLONG_unpack: Callable[[bytes], tuple[int]] | None = None
        self.AG_pack: Callable[[int], bytes] | None = None
        self.AG_unpack: Callable[[bytes], tuple[int]] | None = None

        # Initialize state variables
        self.mta: types.MtaType = types.MtaType(None, None)
        self.currentDaqPtr: Any = None
        self.currentProtectionStatus: dict[str, bool] | None = None

        # Configuration for seed and key
        self.seed_n_key_dll: str | None = self.config.seed_n_key_dll
        self.seed_n_key_function: Callable | None = self.config.seed_n_key_function
        self.seed_n_key_dll_same_bit_width: bool = self.config.seed_n_key_dll_same_bit_width
        self.disconnect_response_optional: bool = self.config.disconnect_response_optional

        # Initialize slave properties
        self.slaveProperties: SlaveProperties = SlaveProperties()
        self.slaveProperties.pgmProcessor = SlaveProperties()
        self.slaveProperties.transport_layer = self.transport_name.upper()

    def __enter__(self):
        """Context manager entry part.

        This method is called when entering a context manager block.
        It connects to the XCP slave and returns the Master instance.

        Returns
        -------
        Master
            The Master instance
        """
        self.transport.connect()
        return self

    def __exit__(
            self, exc_type: type[BaseException] | None, exc_val: BaseException | None,
            exc_tb
    ) -> None:
        """Context manager exit part.

        This method is called when exiting a context manager block.
        It closes the connection to the XCP slave and logs any exceptions.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            The type of the exception that was raised, or None if no exception was raised
        exc_val : BaseException | None
            The exception instance that was raised, or None if no exception was raised
        exc_tb : traceback.TracebackType | None
            The traceback of the exception that was raised, or None if no exception was raised
        """
        # Close the connection to the XCP slave
        self.close()

        # Handle any exceptions that were raised
        if exc_type is not None:
            self.succeeded = False
            self.logger.error("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))

    def _setService(self, service: Any) -> None:
        """Record the currently processed service.

        This method is called by the transport layer to record the
        currently processed service.

        Parameters
        ----------
        service : Any
            The service being processed, typically a `pyxcp.types.Command`

        Note
        ----
        Internal Function, only to be used by transport-layer.
        """
        self.service = service

    def close(self) -> None:
        """Close the transport layer connection.

        This method finalizes the policy and closes the transport layer connection.
        It should be called when the Master instance is no longer needed.
        """
        self.transport.policy.finalize()
        self.transport.close()

    # Mandatory Commands.
    @wrapped
    def connect(self, mode: int = 0x00) -> types.ConnectResponse:
        """Build up connection to an XCP slave.

        Before the actual XCP traffic starts a connection is required.
        This method sends a CONNECT command to the slave and processes
        the response to set up various properties of the slave.

        Parameters
        ----------
        mode : int, optional
            Connection mode, by default 0x00 (normal mode)

        Returns
        -------
        types.ConnectResponse
            Response object containing fundamental client properties

        Note
        ----
        Every XCP slave supports at most one connection,
        more attempts to connect are silently ignored.
        """
        # Send CONNECT command to the slave
        response = self.transport.request(types.Command.CONNECT, mode & 0xFF)

        # First get byte-order from partial response
        result_partial = types.ConnectResponsePartial.parse(response)
        byte_order = result_partial.commModeBasic.byteOrder

        # Parse the full response with the correct byte order
        result = types.ConnectResponse.parse(response, byteOrder=byte_order)

        # Set up byte order dependent properties
        self._setup_slave_properties(result, byte_order)

        # Set up byte order dependent packers and unpackers
        self._setup_packers_and_unpackers(byte_order)

        # Set up address granularity dependent properties
        self._setup_address_granularity()

        return result

    def _setup_slave_properties(self, result: types.ConnectResponse, byte_order: types.ByteOrder) -> None:
        """Set up slave properties based on the connect response.

        Parameters
        ----------
        result : types.ConnectResponse
            The parsed connect response
        byte_order : types.ByteOrder
            The byte order reported by the slave
        """
        # Set basic properties
        self.slaveProperties.byteOrder = byte_order
        self.slaveProperties.maxCto = result.maxCto
        self.slaveProperties.maxDto = result.maxDto

        # Set resource support flags
        self.slaveProperties.supportsPgm = result.resource.pgm
        self.slaveProperties.supportsStim = result.resource.stim
        self.slaveProperties.supportsDaq = result.resource.daq
        self.slaveProperties.supportsCalpag = result.resource.calpag

        # Set communication mode properties
        self.slaveProperties.slaveBlockMode = result.commModeBasic.slaveBlockMode
        self.slaveProperties.addressGranularity = result.commModeBasic.addressGranularity
        self.slaveProperties.optionalCommMode = result.commModeBasic.optional

        # Set version information
        self.slaveProperties.protocolLayerVersion = result.protocolLayerVersion
        self.slaveProperties.transportLayerVersion = result.transportLayerVersion

        # Calculate derived properties
        self.slaveProperties.maxWriteDaqMultipleElements = (
            0 if self.slaveProperties.maxCto < 10 else int((self.slaveProperties.maxCto - 2) // 8)
        )

        # Initialize bytesPerElement (will be set in _setup_address_granularity)
        self.slaveProperties.bytesPerElement = None

    def _setup_packers_and_unpackers(self, byte_order: types.ByteOrder) -> None:
        """Set up byte order dependent packers and unpackers.

        Parameters
        ----------
        byte_order : types.ByteOrder
            The byte order reported by the slave
        """
        # Determine byte order prefix for struct format strings
        byte_order_prefix = "<" if byte_order == types.ByteOrder.INTEL else ">"

        # Create packers and unpackers for different data types
        self.BYTE_pack = makeBytePacker(byte_order_prefix)
        self.BYTE_unpack = makeByteUnpacker(byte_order_prefix)
        self.WORD_pack = makeWordPacker(byte_order_prefix)
        self.WORD_unpack = makeWordUnpacker(byte_order_prefix)
        self.DWORD_pack = makeDWordPacker(byte_order_prefix)
        self.DWORD_unpack = makeDWordUnpacker(byte_order_prefix)
        self.DLONG_pack = makeDLongPacker(byte_order_prefix)
        self.DLONG_unpack = makeDLongUnpacker(byte_order_prefix)

    def _setup_address_granularity(self) -> None:
        """Set up address granularity dependent properties and packers/unpackers."""
        # Set up address granularity dependent packers and unpackers
        if self.slaveProperties.addressGranularity == types.AddressGranularity.BYTE:
            self.AG_pack = struct.Struct("<B").pack
            self.AG_unpack = struct.Struct("<B").unpack
            self.slaveProperties.bytesPerElement = 1
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.WORD:
            self.AG_pack = self.WORD_pack
            self.AG_unpack = self.WORD_unpack
            self.slaveProperties.bytesPerElement = 2
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            self.AG_pack = self.DWORD_pack
            self.AG_unpack = self.DWORD_unpack
            self.slaveProperties.bytesPerElement = 4
            # self.connected = True
        status = self.getStatus()
        if status.sessionStatus.daqRunning:
            # TODO: resume
            self.startStopSynch(0x00)

    @wrapped
    def disconnect(self) -> bytes:
        """Release the connection to the XCP slave.

        This method sends a DISCONNECT command to the slave, which releases
        the connection. Thereafter, no further communication with the slave
        is possible (besides `connect`).

        Returns
        -------
        bytes
            The raw response from the slave, typically empty

        Note
        -----
        - If DISCONNECT is currently not possible, ERR_CMD_BUSY will be returned.
        - While XCP spec. requires a response, this behavior can be made optional by adding
            - `DISCONNECT_RESPONSE_OPTIONAL = true` (TOML)
            - `"DISCONNECT_RESPONSE_OPTIONAL": true` (JSON)
            to your configuration file.
        """
        # Send DISCONNECT command to the slave
        if self.disconnect_response_optional:
            response = self.transport.request_optional_response(types.Command.DISCONNECT)
        else:
            response = self.transport.request(types.Command.DISCONNECT)

        return response

    @wrapped
    def getStatus(self) -> types.GetStatusResponse:
        """Get current status information of the slave device.

        This method sends a GET_STATUS command to the slave and processes
        the response to get information about the current status of the slave.
        This includes the status of the resource protection, pending store
        requests and the general status of data acquisition and stimulation.

        Returns
        -------
        types.GetStatusResponse
            Response object containing status information
        """
        # Send GET_STATUS command to the slave
        response = self.transport.request(types.Command.GET_STATUS)

        # Parse the response with the correct byte order
        result = types.GetStatusResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

        # Update the current protection status
        self._setProtectionStatus(result.resourceProtectionStatus)

        return result

    @wrapped
    def synch(self) -> bytes:
        """Synchronize command execution after timeout conditions.

        This method sends a SYNCH command to the slave, which synchronizes
        command execution after timeout conditions. This is useful when
        the slave has timed out and needs to be resynchronized.

        Returns
        -------
        bytes
            The raw response from the slave
        """
        # Send SYNCH command to the slave
        response = self.transport.request(types.Command.SYNCH)
        return response

    @wrapped
    def getCommModeInfo(self) -> types.GetCommModeInfoResponse:
        """Get optional information on different Communication Modes supported
        by the slave.

        This method sends a GET_COMM_MODE_INFO command to the slave and processes
        the response to get information about the communication modes supported
        by the slave.

        Returns
        -------
        types.GetCommModeInfoResponse
            Response object containing communication mode information
        """
        # Send GET_COMM_MODE_INFO command to the slave
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)

        # Parse the response with the correct byte order
        result = types.GetCommModeInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

        # Update slave properties with communication mode information
        self._update_comm_mode_properties(result)

        return result

    def _update_comm_mode_properties(self, result: types.GetCommModeInfoResponse) -> None:
        """Update slave properties with communication mode information.

        Parameters
        ----------
        result : types.GetCommModeInfoResponse
            The parsed GET_COMM_MODE_INFO response
        """
        # Set optional communication mode properties
        self.slaveProperties.interleavedMode = result.commModeOptional.interleavedMode
        self.slaveProperties.masterBlockMode = result.commModeOptional.masterBlockMode

        # Set basic communication properties
        self.slaveProperties.maxBs = result.maxBs
        self.slaveProperties.minSt = result.minSt
        self.slaveProperties.queueSize = result.queueSize
        self.slaveProperties.xcpDriverVersionNumber = result.xcpDriverVersionNumber

    @wrapped
    def getId(self, mode: int) -> types.GetIDResponse:
        """Get identification information from the slave device.

        This command is used for automatic session configuration and for
        slave device identification. It sends a GET_ID command to the slave
        and processes the response to get identification information.

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
        types.GetIDResponse
            Response object containing identification information
        """
        # Send GET_ID command to the slave
        response = self.transport.request(types.Command.GET_ID, mode)
        result = types.GetIDResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        result.length = self.DWORD_unpack(response[3:7])[0]

        return result

    @wrapped
    def setRequest(self, mode: int, session_configuration_id: int) -> bytes:
        """Request to save data to non-volatile memory.

        This method sends a SET_REQUEST command to the slave, which requests
        the slave to save data to non-volatile memory. The data to be saved
        is specified by the mode parameter.

        Parameters
        ----------
        mode : int (bitfield)
            - 1  Request to store calibration data
            - 2  Request to store DAQ list, no resume
            - 4  Request to store DAQ list, resume enabled
            - 8  Request to clear DAQ configuration
        session_configuration_id : int
            Identifier for the session configuration

        Returns
        -------
        bytes
            The raw response from the slave
        """
        # Send SET_REQUEST command to the slave
        # Split the session_configuration_id into high and low bytes
        return self.transport.request(
            types.Command.SET_REQUEST,
            mode,
            session_configuration_id >> 8,  # High byte
            session_configuration_id & 0xFF,  # Low byte
        )

    @wrapped
    def getSeed(self, first: int, resource: int) -> types.GetSeedResponse:
        """Get seed from slave for unlocking a protected resource.

        This method sends a GET_SEED command to the slave, which returns a seed
        that can be used to generate a key for unlocking a protected resource.
        The seed is used as input to a key generation algorithm, and the resulting
        key is sent back to the slave using the unlock method.

        Parameters
        ----------
        first : int
            - 0 - first part of seed
            - 1 - remaining part
        resource : int
            - Mode == 0 - Resource to unlock
            - Mode == 1 - Don't care

        Returns
        -------
        types.GetSeedResponse
            Response object containing the seed

        Note
        ----
        For CAN transport, the seed may be split across multiple frames if it's
        longer than the maximum DLC. In this case, the first byte of the response
        indicates the remaining seed size, and the master must call getSeed
        multiple times until the complete seed is received.
        """
        # Send GET_SEED command to the slave
        response = self.transport.request(types.Command.GET_SEED, first, resource)

        # Handle CAN-specific seed format
        if self.transport_name == "can":
            # For CAN it might happen that the seed is longer than the max DLC
            # In this case the first byte will be the current remaining seed size
            # followed by the seed bytes that can fit in the current frame
            size, seed = response[0], response[1:]

            # Truncate seed if necessary
            if size < len(seed):
                seed = seed[:size]

            # Create and populate response object
            reply = types.GetSeedResponse.parse(
                types.GetSeedResponse.build({"length": size, "seed": bytes(size)}),
                byteOrder=self.slaveProperties.byteOrder,
            )
            reply.seed = seed
            return reply
        else:
            # For other transports, parse the response directly
            return types.GetSeedResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def unlock(self, length: int, key: bytes) -> types.ResourceType:
        """Send key to slave for unlocking a protected resource.

        This method sends an UNLOCK command to the slave, which attempts to
        unlock a protected resource using the provided key. The key is generated
        from the seed obtained using the getSeed method.

        Parameters
        ----------
        length : int
            Indicates the (remaining) number of key bytes
        key : bytes
            The key bytes to send to the slave

        Returns
        -------
        types.ResourceType
            Response object containing the resource protection status

        Note
        ----
        The master has to use :meth:`unlock` in a defined sequence together
        with :meth:`getSeed`. The master can only send an :meth:`unlock` sequence
        if previously there was a :meth:`getSeed` sequence. The master has
        to send the first `unlocking` after a :meth:`getSeed` sequence with
        a Length containing the total length of the key.
        """
        # Send UNLOCK command to the slave
        response = self.transport.request(types.Command.UNLOCK, length, *key)

        # Parse the response with the correct byte order
        result = types.ResourceType.parse(response, byteOrder=self.slaveProperties.byteOrder)

        # Update the current protection status
        self._setProtectionStatus(result)

        return result

    @wrapped
    def setMta(self, address: int, address_ext: int = 0x00) -> bytes:
        """Set Memory Transfer Address in slave.

        This method sends a SET_MTA command to the slave, which sets the
        Memory Transfer Address (MTA) to the specified address. The MTA is
        used by various commands that transfer data between the master and
        the slave.

        Parameters
        ----------
        address : int
            The memory address to set
        address_ext : int, optional
            The address extension, by default 0x00

        Returns
        -------
        bytes
            The raw response from the slave

        Note
        ----
        The MTA is used by :meth:`buildChecksum`, :meth:`upload`, :meth:`download`, :meth:`downloadNext`,
        :meth:`downloadMax`, :meth:`modifyBits`, :meth:`programClear`, :meth:`program`, :meth:`programNext`
        and :meth:`programMax`.
        """
        # Keep track of MTA (needed for error-handling)
        self.mta = types.MtaType(address, address_ext)

        # Pack the address into bytes
        addr = self.DWORD_pack(address)

        # Send SET_MTA command to the slave
        return self.transport.request(types.Command.SET_MTA, 0, 0, address_ext, *addr)

    @wrapped
    def upload(self, length: int) -> bytes:
        """Transfer data from slave to master.

        This method sends an UPLOAD command to the slave, which transfers
        data from the slave to the master. The data is read from the memory
        address specified by the MTA, which must be set before calling this
        method.

        Parameters
        ----------
        length : int
            Number of elements (address granularity) to upload

        Returns
        -------
        bytes
            The uploaded data

        Note
        ----
        Address is set via :meth:`setMta` (Some services like :meth:`getID` also set the MTA).
        """
        # Calculate the number of bytes to upload
        byte_count = length * self.slaveProperties.bytesPerElement

        # Send UPLOAD command to the slave
        response = self.transport.request(types.Command.UPLOAD, length)

        # Handle block mode for large uploads
        if byte_count > (self.slaveProperties.maxCto - 1):
            # Receive the remaining bytes in block mode
            block_response = self.transport.block_receive(length_required=(byte_count - len(response)))
            response += block_response
        # Handle CAN-specific upload format
        elif self.transport_name == "can":
            # Larger sizes will send in multiple CAN messages
            # Each valid message will start with 0xFF followed by the upload bytes
            # The last message might be padded to the required DLC
            remaining_bytes = byte_count - len(response)
            while remaining_bytes:
                if len(self.transport.resQueue):
                    data = self.transport.resQueue.popleft()
                    response += data[1: remaining_bytes + 1]
                    remaining_bytes = byte_count - len(response)
                else:
                    short_sleep()
        return response

    @wrapped
    def shortUpload(self, length: int, address: int, address_ext: int = 0x00) -> bytes:
        """Transfer data from slave to master with address information.

        This method sends a SHORT_UPLOAD command to the slave, which transfers
        data from the slave to the master. Unlike the :meth:`upload` method,
        this method includes the address information in the command, so it
        doesn't require setting the MTA first.

        Parameters
        ----------
        length : int
            Number of elements (address granularity) to upload
        address : int
            The memory address to read from
        address_ext : int, optional
            The address extension, by default 0x00

        Returns
        -------
        bytes
            The uploaded data
        """
        # Pack the address into bytes
        addr = self.DWORD_pack(address)

        # Calculate the number of bytes to upload
        byte_count = length * self.slaveProperties.bytesPerElement
        max_byte_count = self.slaveProperties.maxCto - 1

        # Check if the requested byte count exceeds the maximum
        if byte_count > max_byte_count:
            self.logger.warn(f"SHORT_UPLOAD: {byte_count} bytes exceeds the maximum value of {max_byte_count}.")

        # Send SHORT_UPLOAD command to the slave
        response = self.transport.request(types.Command.SHORT_UPLOAD, length, 0, address_ext, *addr)

        # Return only the requested number of bytes
        return response[:byte_count]

    @wrapped
    def buildChecksum(self, blocksize: int) -> types.BuildChecksumResponse:
        """Build checksum over memory range.

        This method sends a BUILD_CHECKSUM command to the slave, which calculates
        a checksum over a memory range. The memory range starts at the address
        specified by the MTA and has a size of `blocksize` elements.

        Parameters
        ----------
        blocksize : int
            The number of elements (address granularity) to include in the checksum

        Returns
        -------
        types.BuildChecksumResponse
            Response object containing the checksum information

        Note
        ----
        Address is set via :meth:`setMta`

        See Also
        --------
        :mod:`~pyxcp.checksum`
        """
        # Pack the blocksize into bytes
        bs = self.DWORD_pack(blocksize)

        # Send BUILD_CHECKSUM command to the slave
        response = self.transport.request(types.Command.BUILD_CHECKSUM, 0, 0, 0, *bs)

        # Parse the response with the correct byte order
        return types.BuildChecksumResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def transportLayerCmd(self, sub_command: int, *data: bytes) -> bytes:
        """Execute transfer-layer specific command.

        This method sends a TRANSPORT_LAYER_CMD command to the slave, which
        executes a transport-layer specific command. The exact behavior of
        this command depends on the transport layer being used.

        Parameters
        ----------
        sub_command : int
            The sub-command to execute
        *data : bytes
            Variable number of data bytes to send with the command

        Returns
        -------
        bytes
            The raw response from the slave, or None if no response is expected

        Note
        ----
        For details refer to XCP specification.
        """
        # Send TRANSPORT_LAYER_CMD command to the slave
        return self.transport.request_optional_response(types.Command.TRANSPORT_LAYER_CMD, sub_command, *data)

    @wrapped
    def userCmd(self, sub_command: int, data: bytes) -> bytes:
        """Execute proprietary command implemented in your XCP client.

        This method sends a USER_CMD command to the slave, which executes
        a proprietary command implemented in the XCP client. The exact behavior
        of this command depends on the XCP client vendor.

        Parameters
        ----------
        sub_command : int
            The sub-command to execute
        data : bytes
            The data bytes to send with the command

        Returns
        -------
        bytes
            The raw response from the slave

        Note
        ----
        For details refer to your XCP client vendor.
        """
        # Send USER_CMD command to the slave
        return self.transport.request(types.Command.USER_CMD, sub_command, *data)

    @wrapped
    def getVersion(self) -> types.GetVersionResponse:
        """Get version information from the slave.

        This method sends a GET_VERSION command to the slave, which returns
        detailed information about the implemented protocol layer version
        of the XCP slave and the transport layer currently in use.

        Returns
        -------
        types.GetVersionResponse
            Response object containing version information
        """
        # Send GET_VERSION command to the slave
        response = self.transport.request(types.Command.GET_VERSION)

        # Parse the response with the correct byte order
        result = types.GetVersionResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

        # Update slave properties with version information
        self._update_version_properties(result)

        return result

    def _update_version_properties(self, result: types.GetVersionResponse) -> None:
        """Update slave properties with version information.

        Parameters
        ----------
        result : types.GetVersionResponse
            The parsed GET_VERSION response
        """
        # Set version information
        self.slaveProperties.protocolMajor = result.protocolMajor
        self.slaveProperties.protocolMinor = result.protocolMinor
        self.slaveProperties.transportMajor = result.transportMajor
        self.slaveProperties.transportMinor = result.transportMinor

    def fetch(self, length: int, limit_payload: int = None) -> bytes:  # TODO: pull
        """Convenience function for data-transfer from slave to master.

        This method transfers data from the slave to the master in chunks,
        handling the details of breaking up large transfers into smaller
        pieces. It's not part of the XCP Specification but provides a
        convenient way to fetch data.

        Parameters
        ----------
        length : int
            The number of bytes to fetch
        limit_payload : int, optional
            Transfer less bytes than supported by transport-layer, by default None

        Returns
        -------
        bytes
            The fetched data

        Raises
        ------
        ValueError
            If limit_payload is less than 8 bytes

        Note
        ----
        Address is not included because of services implicitly setting
        address information like :meth:`getID`.
        """
        # Validate limit_payload
        if limit_payload is not None and limit_payload < 8:
            raise ValueError(f"Payload must be at least 8 bytes - given: {limit_payload}")

        # Determine maximum payload size
        slave_block_mode = self.slaveProperties.slaveBlockMode
        max_payload = 255 if slave_block_mode else self.slaveProperties.maxCto - 1

        # Apply limit_payload if specified
        payload = min(limit_payload, max_payload) if limit_payload else max_payload

        # Calculate number of chunks and remaining bytes
        chunk_size = payload
        chunks = range(length // chunk_size)
        remaining = length % chunk_size

        # Fetch data in chunks
        result = []
        for _ in chunks:
            data = self.upload(chunk_size)
            result.extend(data[:chunk_size])

        # Fetch remaining bytes
        if remaining:
            data = self.upload(remaining)
            result.extend(data[:remaining])

        return bytes(result)

    pull = fetch  # fetch() may be completely replaced by pull() someday.

    def push(self, address: int, address_ext: int, data: bytes, callback: Callable[[int], None] | None = None) -> None:
        """Convenience function for data-transfer from master to slave.

        This method transfers data from the master to the slave in chunks,
        handling the details of breaking up large transfers into smaller
        pieces. It's not part of the XCP Specification but provides a
        convenient way to push data.

        Parameters
        ----------
        address : int
            The memory address to write to
        address_ext : int
            The address extension
        data : bytes
            The data bytes to write
        callback : Callable[[int], None], optional
            A callback function that is called with the percentage of completion,
            by default None

        Note
        ----
        This method uses the download and downloadNext methods internally.
        """
        # Use the generalized downloader to transfer the data
        self._generalized_downloader(
            address=address,
            address_ext=address_ext,
            data=data,
            maxCto=self.slaveProperties.maxCto,
            maxBs=self.slaveProperties.maxBs,
            minSt=self.slaveProperties.minSt,
            master_block_mode=self.slaveProperties.masterBlockMode,
            dl_func=self.download,
            dl_next_func=self.downloadNext,
            callback=callback,
        )

    def flash_program(self, address: int, data: bytes, callback: Callable[[int], None] | None = None) -> None:
        """Convenience function for flash programming.

        This method programs flash memory on the slave in chunks, handling
        the details of breaking up large transfers into smaller pieces.
        It's not part of the XCP Specification but provides a convenient
        way to program flash memory.

        Parameters
        ----------
        address : int
            The memory address to program
        data : bytes
            The data bytes to program
        callback : Callable[[int], None], optional
            A callback function that is called with the percentage of completion,
            by default None

        Note
        ----
        This method uses the program and programNext methods internally.
        It automatically uses the programming-specific parameters from the
        slave properties (maxCtoPgm, maxBsPgm, minStPgm, masterBlockMode).
        """
        # Use the generalized downloader to program the flash
        self._generalized_downloader(
            address=address,
            data=data,
            maxCto=self.slaveProperties.pgmProcessor.maxCtoPgm,
            maxBs=self.slaveProperties.pgmProcessor.maxBsPgm,
            minSt=self.slaveProperties.pgmProcessor.minStPgm,
            master_block_mode=self.slaveProperties.pgmProcessor.masterBlockMode,
            dl_func=self.program,
            dl_next_func=self.programNext,
            callback=callback,
        )

    def _generalized_downloader(
            self,
            address: int,
            address_ext: int,
            data: bytes,
            maxCto: int,
            maxBs: int,
            minSt: int,
            master_block_mode: bool,
            dl_func: Callable[[bytes, int, bool], Any],
            dl_next_func: Callable[[bytes, int, bool], Any],
            callback: Callable[[int], None] | None = None,
    ) -> None:
        """Generic implementation for downloading data to the slave.

        This method is a generic implementation for downloading data to the slave.
        It handles the details of breaking up large transfers into smaller pieces,
        and supports both master block mode and normal mode.

        Parameters
        ----------
        address : int
            The memory address to write to
        address_ext : int
            The address extension
        data : bytes
            The data bytes to write
        maxCto : int
            Maximum Command Transfer Object size
        maxBs : int
            Maximum Block Size
        minSt : int
            Minimum Separation Time in 100µs units
        master_block_mode : bool
            Whether to use master block mode
        dl_func : Callable[[bytes, int, bool], Any]
            Function to use for the first download packet
        dl_next_func : Callable[[bytes, int, bool], Any]
            Function to use for subsequent download packets
        callback : Callable[[int], None], optional
            A callback function that is called with the percentage of completion,
            by default None
        """
        # Set the Memory Transfer Address
        self.setMta(address, address_ext)

        # Convert minSt from 100µs units to seconds
        minSt_seconds = minSt / 10000.0

        # Create a partial function for block downloading
        block_downloader = functools.partial(
            self._block_downloader,
            dl_func=dl_func,
            dl_next_func=dl_next_func,
            minSt=minSt_seconds,
        )

        # Calculate total length and maximum payload size
        total_length = len(data)
        if master_block_mode:
            max_payload = min(maxBs * (maxCto - 2), 255)
        else:
            max_payload = maxCto - 2

        # Initialize offset
        offset = 0

        # Handle master block mode
        if master_block_mode:
            self._download_master_block_mode(data, total_length, max_payload, offset, block_downloader, callback)
        # Handle normal mode
        else:
            self._download_normal_mode(data, total_length, max_payload, offset, dl_func, callback)

    def _download_master_block_mode(
            self,
            data: bytes,
            total_length: int,
            max_payload: int,
            offset: int,
            block_downloader: Callable[[bytes], Any],
            callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download data using master block mode.

        Parameters
        ----------
        data : bytes
            The data bytes to write
        total_length : int
            The total length of the data
        max_payload : int
            Maximum payload size
        offset : int
            Starting offset in the data
        block_downloader : Callable[[bytes], Any]
            Function to use for downloading blocks
        callback : Callable[[int], None], optional
            A callback function that is called with the percentage of completion,
            by default None
        """
        remaining = total_length
        blocks = range(total_length // max_payload)
        percent_complete = 1
        remaining_block_size = total_length % max_payload

        # Process full blocks
        for _ in blocks:
            block = data[offset: offset + max_payload]
            block_downloader(block)
            offset += max_payload
            remaining -= max_payload

            # Call callback if provided
            if callback and remaining <= total_length - (total_length / 100) * percent_complete:
                callback(percent_complete)
                percent_complete += 1

        # Process remaining partial block
        if remaining_block_size:
            block = data[offset: offset + remaining_block_size]
            block_downloader(block)
            if callback:
                callback(percent_complete)

    def _download_normal_mode(
            self,
            data: bytes,
            total_length: int,
            max_payload: int,
            offset: int,
            dl_func: Callable[[bytes, int, bool], Any],
            callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download data using normal mode.

        Parameters
        ----------
        data : bytes
            The data bytes to write
        total_length : int
            The total length of the data
        max_payload : int
            Maximum payload size
        offset : int
            Starting offset in the data
        dl_func : Callable[[bytes, int, bool], Any]
            Function to use for downloading
        callback : Callable[[int], None], optional
            A callback function that is called with the percentage of completion,
            by default None
        """
        chunk_size = max_payload
        chunks = range(total_length // chunk_size)
        remaining = total_length % chunk_size
        percent_complete = 1
        callback_remaining = total_length

        # Process full chunks
        for _ in chunks:
            block = data[offset: offset + max_payload]
            dl_func(block, max_payload, last=False)
            offset += max_payload
            callback_remaining -= chunk_size

            # Call callback if provided
            if callback and callback_remaining <= total_length - (total_length / 100) * percent_complete:
                callback(percent_complete)
                percent_complete += 1

        # Process remaining partial chunk
        if remaining:
            block = data[offset: offset + remaining]
            dl_func(block, remaining, last=True)
            if callback:
                callback(percent_complete)

    def _block_downloader(
            self,
            data: bytes,
            dl_func: Callable[[bytes, int, bool], Any] | None = None,
            dl_next_func: Callable[[bytes, int, bool], Any] | None = None,
            minSt: float = 0.0,
    ) -> None:
        """Re-usable block downloader for transferring data in blocks.

        This method breaks up a block of data into packets and sends them
        using the provided download functions. It handles the details of
        calculating packet sizes, setting the 'last' flag, and applying
        the minimum separation time between packets.

        Parameters
        ----------
        data : bytes
            The data bytes to download
        dl_func : Callable[[bytes, int, bool], Any] | None, optional
            Function to use for the first download packet,
            usually :meth:`download` or :meth:`program`, by default None
        dl_next_func : Callable[[bytes, int, bool], Any] | None, optional
            Function to use for subsequent download packets,
            usually :meth:`downloadNext` or :meth:`programNext`, by default None
        minSt : float, optional
            Minimum separation time between frames in seconds, by default 0.0
        """
        # Calculate sizes and offsets
        length = len(data)
        max_packet_size = self.slaveProperties.maxCto - 2  # Command ID + Length
        packets = range(length // max_packet_size)
        offset = 0
        remaining = length % max_packet_size
        remaining_block_size = length

        # Process full packets
        index = 0
        for index in packets:
            # Extract packet data
            packet_data = data[offset: offset + max_packet_size]

            # Determine if this is the last packet
            last = (remaining_block_size - max_packet_size) == 0

            # Send packet using appropriate function
            if index == 0:
                # First packet: use dl_func and transmit the complete length
                dl_func(packet_data, length, last)
            else:
                # Subsequent packets: use dl_next_func
                dl_next_func(packet_data, remaining_block_size, last)

            # Update offsets and remaining size
            offset += max_packet_size
            remaining_block_size -= max_packet_size

            # Apply minimum separation time
            delay(minSt)

        # Process remaining partial packet
        if remaining:
            # Extract remaining data
            packet_data = data[offset: offset + remaining]

            # Send packet using appropriate function
            if index == 0:
                # If there were no full packets, use dl_func
                # (length of data is smaller than maxCto - 2)
                dl_func(packet_data, remaining, last=True)
            else:
                # Otherwise use dl_next_func
                dl_next_func(packet_data, remaining, last=True)

            # Apply minimum separation time
            delay(minSt)

    @wrapped
    def download(self, data: bytes, block_mode_length: int | None = None, last: bool = False):
        """Transfer data from master to slave.

        Parameters
        ----------
        data : bytes
            Data to send to slave.
        block_mode_length : int or None
            for block mode, the download request must contain the length of the whole block,
            not just the length in the current packet. The whole block length can be given here for block-mode
            transfers. For normal mode, the length indicates the actual packet's payload length.

        Note
        ----
        Adress is set via :meth:`setMta`
        """

        if block_mode_length is None or last:
            # standard mode
            length = len(data)
            response = self.transport.request(types.Command.DOWNLOAD, length, *data)
            return response
        else:
            # block mode
            if not isinstance(block_mode_length, int):
                raise TypeError("block_mode_length must be int!")
            self.transport.block_request(types.Command.DOWNLOAD, block_mode_length, *data)
            return None

    @wrapped
    def downloadNext(self, data: bytes, remaining_block_length: int, last: bool = False):
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
            response = self.transport.request(types.Command.DOWNLOAD_NEXT, remaining_block_length, *data)
            return response
        else:
            # the slave device won't respond to consecutive DOWNLOAD_NEXT packets in block mode,
            # so we must not wait for any response
            self.transport.block_request(types.Command.DOWNLOAD_NEXT, remaining_block_length, *data)
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
    def shortDownload(self, address: int, address_ext: int, data: bytes):
        length = len(data)
        addr = self.DWORD_pack(address)
        return self.transport.request(types.Command.SHORT_DOWNLOAD, length, 0, address_ext, *addr, *data)

    @wrapped
    def modifyBits(self, shift_value: int, and_mask: int, xor_mask: int):
        # A = ( (A) & ((~((dword)(((word)~MA)<<S))) )^((dword)(MX<<S)) )
        am = self.WORD_pack(and_mask)
        xm = self.WORD_pack(xor_mask)
        return self.transport.request(types.Command.MODIFY_BITS, shift_value, *am, *xm)

    # Page Switching Commands (PAG)
    @wrapped
    def setCalPage(self, mode: int, logical_data_segment: int, logical_data_page: int):
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
        return self.transport.request(types.Command.SET_CAL_PAGE, mode, logical_data_segment, logical_data_page)

    @wrapped
    def getCalPage(self, mode: int, logical_data_segment: int):
        """Get calibration page

        Parameters
        ----------
        mode : int
        logicalDataSegment : int
        """
        response = self.transport.request(types.Command.GET_CAL_PAGE, mode, logical_data_segment)
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
    def getSegmentInfo(self, mode: int, segment_number: int, segment_info: int, mapping_index: int):
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
            types.Command.GET_SEGMENT_INFO,
            mode,
            segment_number,
            segment_info,
            mapping_index,
        )
        if mode == 0:
            return types.GetSegmentInfoMode0Response.parse(response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 1:
            return types.GetSegmentInfoMode1Response.parse(response, byteOrder=self.slaveProperties.byteOrder)
        elif mode == 2:
            return types.GetSegmentInfoMode2Response.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getPageInfo(self, segment_number: int, page_number: int):
        """Get specific information for a page.

        Parameters
        ----------
        segmentNumber : int
        pageNumber : int
        """
        response = self.transport.request(types.Command.GET_PAGE_INFO, 0, segment_number, page_number)
        return (
            types.PageProperties.parse(bytes([response[0]]), byteOrder=self.slaveProperties.byteOrder),
            response[1],
        )

    @wrapped
    def setSegmentMode(self, mode: int, segment_number: int):
        """Set mode for a segment.

        Parameters
        ----------
        mode : int (bitfield)
            1 = enable FREEZE Mode
        segmentNumber : int
        """
        return self.transport.request(types.Command.SET_SEGMENT_MODE, mode, segment_number)

    @wrapped
    def getSegmentMode(self, segment_number: int):
        """Get mode for a segment.

        Parameters
        ----------
        segmentNumber : int
        """
        response = self.transport.request(types.Command.GET_SEGMENT_MODE, 0, segment_number)
        if response:
            return response[1]

    @wrapped
    def copyCalPage(self, src_segment: int, src_page: int, dst_segment: int, dst_page: int):
        """Copy page.

        Parameters
        ----------
        srcSegment : int
        srcPage : int
        dstSegment : int
        dstPage : int
        """
        return self.transport.request(types.Command.COPY_CAL_PAGE, src_segment, src_page, dst_segment, dst_page)

    # DAQ

    @wrapped
    def setDaqPtr(self, daq_list_number: int, odt_number: int, odt_entry_number: int):
        self.currentDaqPtr = types.DaqPtr(daq_list_number, odt_number, odt_entry_number)  # Needed for errorhandling.
        daq_list = self.WORD_pack(daq_list_number)
        response = self.transport.request(types.Command.SET_DAQ_PTR, 0, *daq_list, odt_number, odt_entry_number)
        self.stim.setDaqPtr(daq_list_number, odt_number, odt_entry_number)
        return response

    @wrapped
    def clearDaqList(self, daq_list_number: int):
        """Clear DAQ list configuration.

        Parameters
        ----------
        daqListNumber : int
        """
        daq_list = self.WORD_pack(daq_list_number)
        result = self.transport.request(types.Command.CLEAR_DAQ_LIST, 0, *daq_list)
        self.stim.clearDaqList(daq_list_number)
        return result

    @wrapped
    def writeDaq(self, bit_offset: int, entry_size: int, address_ext: int, address: int):
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
        result = self.transport.request(types.Command.WRITE_DAQ, bit_offset, entry_size, address_ext, *addr)
        self.stim.writeDaq(bit_offset, entry_size, address_ext, address)
        return result

    @wrapped
    def setDaqListMode(self, mode: int, daq_list_number: int, event_channel_number: int, prescaler: int, priority: int):
        dln = self.WORD_pack(daq_list_number)
        ecn = self.WORD_pack(event_channel_number)
        self.stim.setDaqListMode(mode, daq_list_number, event_channel_number, prescaler, priority)
        return self.transport.request(types.Command.SET_DAQ_LIST_MODE, mode, *dln, *ecn, prescaler, priority)

    @wrapped
    def getDaqListMode(self, daq_list_number: int):
        """Get mode from DAQ list.

        Parameters
        ----------
        daqListNumber : int

        Returns
        -------
        `pyxcp.types.GetDaqListModeResponse`
        """
        dln = self.WORD_pack(daq_list_number)
        response = self.transport.request(types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def startStopDaqList(self, mode: int, daq_list_number: int):
        """Start /stop/select DAQ list.

        Parameters
        ----------
        mode : int
            0 = stop
            1 = start
            2 = select
        daqListNumber : int
        """
        dln = self.WORD_pack(daq_list_number)
        response = self.transport.request(types.Command.START_STOP_DAQ_LIST, mode, *dln)
        self.stim.startStopDaqList(mode, daq_list_number)
        first_pid = types.StartStopDaqListResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self.stim.set_first_pid(daq_list_number, first_pid.firstPid)
        return first_pid

    @wrapped
    def startStopSynch(self, mode: int):
        """Start/stop DAQ lists (synchronously).

        Parameters
        ----------
        mode : int
            0 = stop all
            1 = start selected
            2 = stop selected
        """
        res = self.transport.request(types.Command.START_STOP_SYNCH, mode)
        self.stim.startStopSynch(mode)
        return res

    @wrapped
    def writeDaqMultiple(self, daq_elements: dict):
        """Write multiple elements in ODT.

        Parameters
        ----------
        daqElements : list of `dict` containing the following keys: *bitOffset*, *size*, *address*, *addressExt*.
        """
        if len(daq_elements) > self.slaveProperties.maxWriteDaqMultipleElements:
            raise ValueError(f"At most {self.slaveProperties.maxWriteDaqMultipleElements} daqElements are permitted.")
        data = bytearray()
        data.append(len(daq_elements))

        for daq_element in daq_elements:
            data.extend(types.DaqElement.build(daq_element, byteOrder=self.slaveProperties.byteOrder))

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
    def getDaqListInfo(self, daq_list_number: int):
        """Get specific information for a DAQ list.

        Parameters
        ----------
        daqListNumber : int
        """
        dln = self.WORD_pack(daq_list_number)
        response = self.transport.request(types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def getDaqEventInfo(self, event_channel_number: int):
        """Get specific information for an event channel.

        Parameters
        ----------
        eventChannelNumber : int

        Returns
        -------
        `pyxcp.types.GetEventChannelInfoResponse`
        """
        ecn = self.WORD_pack(event_channel_number)
        response = self.transport.request(types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def dtoCtrProperties(self, modifier: int, event_channel: int, related_event_channel: int, mode: int):
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
        data.extend(self.WORD_pack(event_channel))
        data.extend(self.WORD_pack(related_event_channel))
        data.append(mode)
        response = self.transport.request(types.Command.DTO_CTR_PROPERTIES, *data)
        return types.DtoCtrPropertiesResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    @wrapped
    def setDaqPackedMode(
            self, daq_list_number: int, daq_packed_mode: int, dpm_timestamp_mode: int = None,
            dpm_sample_count: int = None
    ):
        """Set DAQ List Packed Mode.

        Parameters
        ----------
        daqListNumber : int
        daqPackedMode : int
        """
        params = []
        dln = self.WORD_pack(daq_list_number)
        params.extend(dln)
        params.append(daq_packed_mode)

        if daq_packed_mode == 1 or daq_packed_mode == 2:
            params.append(dpm_timestamp_mode)
            dsc = self.WORD_pack(dpm_sample_count)
            params.extend(dsc)

        return self.transport.request(types.Command.SET_DAQ_PACKED_MODE, *params)

    @wrapped
    def getDaqPackedMode(self, daq_list_number: int):
        """Get DAQ List Packed Mode.

        This command returns information of the currently active packed mode of
        the addressed DAQ list.

        Parameters
        ----------
        daqListNumber : int
        """
        dln = self.WORD_pack(daq_list_number)
        response = self.transport.request(types.Command.GET_DAQ_PACKED_MODE, *dln)
        return types.GetDaqPackedModeResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    # dynamic
    @wrapped
    def freeDaq(self):
        """Clear dynamic DAQ configuration."""
        result = self.transport.request(types.Command.FREE_DAQ)
        self.stim.freeDaq()
        return result

    @wrapped
    def allocDaq(self, daq_count: int):
        """Allocate DAQ lists.

        Parameters
        ----------
        daqCount : int
            number of DAQ lists to be allocated
        """
        dq = self.WORD_pack(daq_count)
        result = self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)
        self.stim.allocDaq(daq_count)
        return result

    @wrapped
    def allocOdt(self, daq_list_number: int, odt_count: int):
        dln = self.WORD_pack(daq_list_number)
        result = self.transport.request(types.Command.ALLOC_ODT, 0, *dln, odt_count)
        self.stim.allocOdt(daq_list_number, odt_count)
        return result

    @wrapped
    def allocOdtEntry(self, daq_list_number: int, odt_number: int, odt_entries_count: int):
        dln = self.WORD_pack(daq_list_number)
        result = self.transport.request(types.Command.ALLOC_ODT_ENTRY, 0, *dln, odt_number, odt_entries_count)
        self.stim.allocOdtEntry(daq_list_number, odt_number, odt_entries_count)
        return result

    # PGM
    @wrapped
    def programStart(self):
        """Indicate the beginning of a programming sequence.

        Returns
        -------
        `pyxcp.types.ProgramStartResponse`
        """
        response = self.transport.request(types.Command.PROGRAM_START)
        result = types.ProgramStartResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.pgmProcessor.commModePgm = result.commModePgm
        self.slaveProperties.pgmProcessor.maxCtoPgm = result.maxCtoPgm
        self.slaveProperties.pgmProcessor.maxBsPgm = result.maxBsPgm
        self.slaveProperties.pgmProcessor.minStPgm = result.minStPgm
        self.slaveProperties.pgmProcessor.queueSizePgm = result.queueSizePgm
        self.slaveProperties.pgmProcessor.slaveBlockMode = result.commModePgm.slaveBlockMode
        self.slaveProperties.pgmProcessor.interleavedMode = result.commModePgm.interleavedMode
        self.slaveProperties.pgmProcessor.masterBlockMode = result.commModePgm.masterBlockMode
        return result

    @wrapped
    def programClear(self, mode: int, clear_range: int):
        """Clear a part of non-volatile memory.

        Parameters
        ----------
        mode : int
            0x00 = the absolute access mode is active (default)
            0x01 = the functional access mode is active
        clearRange : int
        """
        cr = self.DWORD_pack(clear_range)
        response = self.transport.request(types.Command.PROGRAM_CLEAR, mode, 0, 0, *cr)
        # ERR_ACCESS_LOCKED
        return response

    @wrapped
    def program(self, data: bytes, block_length: int, last: bool = False):
        """Parameters
        ----------
        data : bytes
            Data to send to slave.
        block_mode_length : int
            the program request must contain the length of the whole block, not just the length
            in the current packet.
        last : bool
            Indicates that this is the only packet in the block, because
            the slave device will send the response after this.

        Note
        ----
        Adress is set via :meth:`setMta`
        """
        # d = bytearray()
        # d.append(len(data))
        # if self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
        #    d.extend(b"\x00\x00")  # alignment bytes
        # for e in data:
        #    d.extend(self.AG_pack(e))
        if last:
            # last PROGRAM_NEXT packet in a block: the slave device has to send the response after this.
            response = self.transport.request(types.Command.PROGRAM, block_length, *data)
            return response
        else:
            # the slave device won't respond to consecutive PROGRAM_NEXT packets in block mode,
            # so we must not wait for any response
            self.transport.block_request(types.Command.PROGRAM, block_length, *data)
            return None

    @wrapped
    def programReset(self, wait_for_optional_response=True):
        """Indicate the end of a programming sequence."""
        if wait_for_optional_response:
            return self.transport.request_optional_response(types.Command.PROGRAM_RESET)
        else:
            return self.transport.request(types.Command.PROGRAM_RESET)

    @wrapped
    def getPgmProcessorInfo(self):
        """Get general information on PGM processor."""
        response = self.transport.request(types.Command.GET_PGM_PROCESSOR_INFO)
        result = types.GetPgmProcessorInfoResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)
        self.slaveProperties.pgmProcessor.pgmProperties = result.pgmProperties
        self.slaveProperties.pgmProcessor.maxSector = result.maxSector
        return result

    @wrapped
    def getSectorInfo(self, mode: int, sector_number: int):
        """Get specific information for a sector."""
        response = self.transport.request(types.Command.GET_SECTOR_INFO, mode, sector_number)
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
    def programFormat(self, compression_method: int, encryption_method: int, programming_method: int,
                      access_method: int):
        return self.transport.request(
            types.Command.PROGRAM_FORMAT,
            compression_method,
            encryption_method,
            programming_method,
            access_method,
        )

    @wrapped
    def programNext(self, data: bytes, remaining_block_length: int, last: bool = False):
        # d = bytearray()
        # d.append(len(data))
        # if self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
        #    d.extend(b"\x00\x00")  # alignment bytes
        # for e in data:
        #    d.extend(self.AG_pack(e))
        if last:
            # last PROGRAM_NEXT packet in a block: the slave device has to send the response after this.
            response = self.transport.request(types.Command.PROGRAM_NEXT, remaining_block_length, *data)
            return response
        else:
            # the slave device won't respond to consecutive PROGRAM_NEXT packets in block mode,
            # so we must not wait for any response
            self.transport.block_request(types.Command.PROGRAM_NEXT, remaining_block_length, *data)
            return None

    @wrapped
    def programMax(self, data: bytes):
        d = bytearray()
        if self.slaveProperties.addressGranularity == types.AddressGranularity.WORD:
            d.extend(b"\x00")  # alignment bytes
        elif self.slaveProperties.addressGranularity == types.AddressGranularity.DWORD:
            d.extend(b"\x00\x00\x00")  # alignment bytes
        for e in data:
            d.extend(self.AG_pack(e))
        return self.transport.request(types.Command.PROGRAM_MAX, *d)

    @wrapped
    def programVerify(self, ver_mode: int, ver_type: int, ver_value: int):
        data = bytearray()
        data.extend(self.WORD_pack(ver_type))
        data.extend(self.DWORD_pack(ver_value))
        return self.transport.request(types.Command.PROGRAM_VERIFY, ver_mode, *data)

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
    def timeCorrelationProperties(self, set_properties: int, get_properties_request: int, cluster_id: int):
        response = self.transport.request(
            types.Command.TIME_CORRELATION_PROPERTIES, set_properties, get_properties_request, 0,
            *self.WORD_pack(cluster_id)
        )
        return types.TimeCorrelationPropertiesResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    # Transport layer commands / CAN.

    @broadcasted
    @wrapped
    def getSlaveID(self, mode: int):
        response = self.transportLayerCmd(types.TransportLayerCommands.GET_SLAVE_ID, ord("X"), ord("C"), ord("P"), mode)
        return types.GetSlaveIdResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    def getDaqId(self, daq_list_number: int):
        response = self.transportLayerCmd(types.TransportLayerCommands.GET_DAQ_ID, *self.WORD_pack(daq_list_number))
        # if response:
        return types.GetDaqIdResponse.parse(response, byteOrder=self.slaveProperties.byteOrder)

    def setDaqId(self, daq_list_number: int, identifier: int):
        response = self.transportLayerCmd(
            types.TransportLayerCommands.SET_DAQ_ID, *self.WORD_pack(daq_list_number), *self.DWORD_pack(identifier)
        )
        return response

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
        self.logger.debug(f"BuildChecksum return'd: 0x{cs.checksum:08X} [{cs.checksumType}]")
        self.setMta(addr)
        data = self.fetch(length)
        cc = checksum.check(data, cs.checksumType)
        self.logger.debug(f"Our checksum          : 0x{cc:08X}")
        return cs.checksum == cc

    def getDaqInfo(self, include_event_lists=True):
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
        daq_events = []
        if include_event_lists:
            for ecn in range(dpi.maxEventChannel):
                eci = self.getDaqEventInfo(ecn)
                cycle = eci["eventChannelTimeCycle"]
                maxDaqList = eci["maxDaqList"]
                priority = eci["eventChannelPriority"]
                time_unit = eci["eventChannelTimeUnit"]
                consistency = eci["daqEventProperties"]["consistency"]
                daq_supported = eci["daqEventProperties"]["daq"]
                stim_supported = eci["daqEventProperties"]["stim"]
                packed_supported = eci["daqEventProperties"]["packed"]
                name = self.fetch(eci.eventChannelNameLength)
                if name:
                    name = decode_bytes(name)
                channel = {
                    "name": name,
                    "priority": eci["eventChannelPriority"],
                    "unit": eci["eventChannelTimeUnit"],
                    "cycle": eci["eventChannelTimeCycle"],
                    "maxDaqList": eci["maxDaqList"],
                    "properties": {
                        "consistency": consistency,
                        "daq": daq_supported,
                        "stim": stim_supported,
                        "packed": packed_supported,
                    },
                }
                daq_event_info = DaqEventInfo(
                    name,
                    types.EVENT_CHANNEL_TIME_UNIT_TO_EXP[time_unit],
                    cycle,
                    maxDaqList,
                    priority,
                    consistency,
                    daq_supported,
                    stim_supported,
                    packed_supported,
                )
                daq_events.append(daq_event_info)
                channels.append(channel)
        result["channels"] = channels
        self.stim.setDaqEventInfo(daq_events)
        return result

    def getCurrentProtectionStatus(self):
        """"""
        if self.currentProtectionStatus is None:
            try:
                status = self.getStatus()
            except Exception as e:  # may temporary ERR_OUT_OF_RANGE
                return {"dbg": None, "pgm": None, "stim": None, "daq": None, "calpag": None}
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

        Precondition: Parameter "SEED_N_KEY_DLL" must be present and point to a valid DLL/SO.

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

        from pyxcp.dllif import SeedNKeyError, SeedNKeyResult, getKey

        MAX_PAYLOAD = self.slaveProperties["maxCto"] - 2

        protection_status = self.getCurrentProtectionStatus()
        if any(protection_status.values()) and (not (self.seed_n_key_dll or self.seed_n_key_function)):
            raise RuntimeError(
                "Neither seed-and-key DLL nor function specified, cannot proceed.")  # TODO: ConfigurationError
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
        resource_names = [r.lower() for r in re.split(r"[ ,]", resources) if r]
        for name in resource_names:
            if name not in types.RESOURCE_VALUES:
                raise ValueError(f"Invalid resource name {name!r}.")
            if not protection_status[name]:
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
                    remaining -= result.length
            self.logger.debug(f"Got seed {seed!r} for resource {resource_value!r}.")
            if self.seed_n_key_function:
                key = self.seed_n_key_function(resource_value, bytes(seed))
                self.logger.debug(f"Using seed and key function {self.seed_n_key_function.__name__!r}().")
                result = SeedNKeyResult.ACK
            elif self.seed_n_key_dll:
                self.logger.debug(f"Using seed and key DLL {self.seed_n_key_dll!r}.")
                result, key = getKey(
                    self.logger,
                    self.config.custom_dll_loader,
                    self.seed_n_key_dll,
                    resource_value,
                    bytes(seed),
                    self.seed_n_key_dll_same_bit_width,
                )
            if result == SeedNKeyResult.ACK:
                key = list(key)
                self.logger.debug(f"Unlocking resource {resource_value!r} with key {key!r}.")
                remaining = len(key)
                while key:
                    data = key[:MAX_PAYLOAD]
                    key_len = len(data)
                    self.unlock(remaining, data)
                    key = key[MAX_PAYLOAD:]
                    remaining -= key_len
            else:
                raise SeedNKeyError(f"SeedAndKey DLL returned: {SeedNKeyResult(result).name!r}")

    def identifier(self, id_value: int) -> str:
        """Return the identifier for the given value.
        Use this method instead of calling `getId()` directly.

        Parameters
        ----------
        id_value: int
            For standard identifiers, use the constants from `pyxcp.types.XcpGetIdType`.

        Returns
        -------
        str
        """
        gid = self.getId(id_value)
        if (gid.mode & 0x01) == 0x01:
            value = bytes(gid.identification or b"")
        else:
            value = self.fetch(gid.length)
        return decode_bytes(value)

    def id_scanner(self, scan_ranges: Collection[Collection[int]] | None = None) -> dict[str, str]:
        """Scan for available standard identification types (GET_ID).

        Parameters
        ----------
        scan_ranges: Optional[Collection[Collection[int]]]

        - If parameter is omitted or `None` test every standard identification type (s. GET_ID service)
          plus extensions by Vector Informatik.
        - Else `scan_ranges` must be a list-of-list.
            e.g: [[12, 80], [123], [240, 16, 35]]
                - The first list is a range (closed interval).
                - The second is a single value.
                - The third is a value list.

        Returns
        -------
        Dict[str, str]

        """
        result = {}

        def make_generator(sr):
            STD_IDS = {int(v): k for k, v in types.XcpGetIdType.__members__.items()}
            if sr is None:
                scan_range = STD_IDS.keys()
            else:
                scan_range = []
                if not isinstance(sr, Collection):
                    raise TypeError("scan_ranges must be of type `Collection`")
                for element in sr:
                    if not isinstance(element, Collection):
                        raise TypeError("scan_ranges elements must be of type `Collection`")
                    if not element:
                        raise ValueError("scan_ranges elements cannot be empty")
                    if len(element) == 1:
                        scan_range.append(element[0])  # Single value
                    elif len(element) == 2:
                        start, stop = element  # Value range
                        scan_range.extend(list(range(start, stop + 1)))
                    else:
                        scan_range.extend(element)  # Value list.
            scan_range = sorted(frozenset(scan_range))

            def generate():
                for idx, id_value in enumerate(scan_range):
                    if id_value in STD_IDS:
                        name = STD_IDS[id_value]
                    else:
                        name = f"USER_{idx}"
                    yield id_value, name,

            return generate()

        gen = make_generator(scan_ranges)
        for id_value, name in gen:
            # Avoid noisy warnings while probing
            status, response = self.try_command(self.identifier, id_value, silent=True)
            if status == types.TryCommandResult.OK and response:
                result[name] = response
                continue
            if status == types.TryCommandResult.NOT_IMPLEMENTED:
                # GET_ID not supported by the slave at all → stop scanning
                break
            if status == types.TryCommandResult.XCP_ERROR:
                # Some IDs may not be supported; ignore typical probe errors
                try:
                    err = response.error_code
                except Exception:
                    err = None
                if err in (types.XcpError.ERR_OUT_OF_RANGE, types.XcpError.ERR_CMD_SYNTAX):
                    continue
                # For any other XCP error, keep scanning (best-effort) instead of aborting
                continue
            if status == types.TryCommandResult.OTHER_ERROR:
                raise RuntimeError(f"Error while scanning for ID {id_value}: {response!r}")
        return result

    @property
    def start_datetime(self) -> int:
        """"""
        return self.transport.start_datetime

    def try_command(self, cmd: Callable, *args, **kws) -> tuple[types.TryCommandResult, Any]:
        """Call master functions and handle XCP errors more gracefuly.

        Parameter
        ---------
        cmd: Callable
        args: list
            variable length arguments to `cmd`.
        kws: dict
            keyword arguments to `cmd`.

            `extra_msg`: str
                Additional info to log message (not passed to `cmd`).

        Returns
        -------

        Note
        ----
        Mainly used for plug-and-play applications, e.g. `id_scanner` may confronted with `ERR_OUT_OF_RANGE` errors, which
        is normal for this kind of applications -- or to test for optional commands.
        Use carefuly not to hide serious error causes.
        """
        # Suppress logging of expected XCP negative responses during try_command
        _prev_suppress = is_suppress_xcp_error_log()
        set_suppress_xcp_error_log(True)
        try:
            extra_msg: str | None = kws.get("extra_msg")
            if extra_msg:
                kws.pop("extra_msg")
            else:
                extra_msg = ""
            silent: bool | None = kws.get("silent")
            if silent:
                kws.pop("silent")
            else:
                silent = False
            res = cmd(*args, **kws)
        except SystemExit as e:
            # restore suppression flag before handling
            set_suppress_xcp_error_log(_prev_suppress)
            # print(f"\tUnexpected error while executing command {cmd.__name__!r}: {e!r}")
            if e.error_code == types.XcpError.ERR_CMD_UNKNOWN:
                # This is a rather common use-case, so let the user know that there is some functionality missing.
                if not silent:
                    if extra_msg:
                        self.logger.warning(f"Optional command {cmd.__name__!r} not implemented -- {extra_msg!r}")
                    else:
                        self.logger.warning(f"Optional command {cmd.__name__!r} not implemented.")
                return (types.TryCommandResult.NOT_IMPLEMENTED, e)
            else:
                return (types.TryCommandResult.XCP_ERROR, e)
        except Exception as e:
            return (types.TryCommandResult.OTHER_ERROR, e)
        else:
            return (types.TryCommandResult.OK, res)
        finally:
            # Ensure suppression flag is restored even on success/other exceptions
            with suppress(Exception):
                set_suppress_xcp_error_log(_prev_suppress)


def ticks_to_seconds(ticks, resolution):
    """Convert DAQ timestamp/tick value to seconds.

    Parameters
    ----------
    ticks: int

    unit: `GetDaqResolutionInfoResponse` as returned by :meth:`getDaqResolutionInfo`
    """
    warnings.warn(
        "ticks_to_seconds() deprecated, use factory :func:`make_tick_converter` instead.",
        Warning,
        stacklevel=1,
    )
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
