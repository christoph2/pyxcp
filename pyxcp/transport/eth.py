#!/usr/bin/env python
import socket
import struct
import threading

from pyxcp.cpp_ext.cpp_ext import init_networking
from pyxcp.transport.eth_backend import EthIoBackend, create_eth_backend
from pyxcp.transport.transport_ext import EthProtocol, EthConfig, EthMulticastSender, EthReceiver, FramingError

from pyxcp.transport.base import (
    BaseTransport,
    ChecksumType,
    XcpFramingConfig,
    XcpTransportLayerType,
)

DEFAULT_XCP_PORT = 5555
DEFAULT_XCP_MULTICAST_PORT = 5557  # XCP 1.3: GET_DAQ_CLOCK_MULTICAST
DEFAULT_XCP_DISCOVERY_PORT = 5556  # XCP Ethernet discovery (GET_SLAVE_ID*)
DEFAULT_XCP_DISCOVERY_ADDRESS = "239.255.0.0"

DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS = "239.255.2.1"
DEFAULT_XCP_DISCOVERY_RESPONSE_PORT = 5556


class Eth(BaseTransport):
    """XCP on Ethernet (TCP/UDP) transport.

    Handles XCP-level concerns (framing config, address parameters, PTP
    trigger, GET_DAQ_CLOCK_MULTICAST). The actual byte-level network I/O
    (connect / send / receive-loop) is delegated to an
    :class:`~pyxcp.transport.eth_backend.EthIoBackend` implementation,
    selected via ``config.experimental_backend`` -- this is the seam that
    allows switching between the proven, selectors-based implementation and
    an experimental backend (e.g. a future IOCP-based implementation on
    Windows) without touching this class.
    """

    MAX_DATAGRAM_SIZE = 65535
    HEADER = struct.Struct("<HH")

    def __init__(self, config=None, policy=None, transport_layer_interface: socket.socket | None = None) -> None:
        self.load_config(config)
        framing_config = XcpFramingConfig(
            transport_layer_type=XcpTransportLayerType.ETH,
            header_len=2,
            header_ctr=2,
            header_fill=0,
            tail_fill=False,
            tail_cs=ChecksumType.NO_CHECKSUM,
        )
        super().__init__(config, framing_config, policy, transport_layer_interface)
        eth_config = EthConfig()
        eth_config.host = self.config.host
        eth_config.port = self.config.port
        eth_config.protocol = EthProtocol.UDP if self.config.protocol.upper() == "UDP" else EthProtocol.TCP
        eth_config.ipv6 = self.config.ipv6
        eth_config.use_tcp_no_delay = self.config.tcp_nodelay
        eth_config.iocp_buffer_size = getattr(self.config, "iocp_buffer_size", None)
        eth_config.iocp_receive_queue_depth = getattr(self.config, "iocp_receive_queue_depth", None)
        eth_config.ptp_timestamping = self.config.ptp_timestamping
        address_to_bind: str = self.config.bind_to_address
        bind_to_port: int = self.config.bind_to_port
        eth_config.bind_to = (address_to_bind, bind_to_port) if address_to_bind else None

        init_networking()
        self._multicast_sender = EthMulticastSender()

        backend_name = "iocp" if self.config.experimental_backend else "legacy"
        self._backend: EthIoBackend = create_eth_backend(backend_name, self)
        self._backend.setup(eth_config)

        self._eth_receiver = EthReceiver(
            proto=eth_config.protocol,
            dispatch_handler=self.process_response,
            error_handler=self.on_framing_error,
            max_payload_size=Eth.MAX_DATAGRAM_SIZE,
        )

    def connect(self) -> None:
        if self.status == 0:
            self._backend.connect()
            self.start_listener()

    def start_listener(self) -> None:
        super().start_listener()
        self._backend.start_listening()

    def listen(self) -> None:
        self._backend.listen()

    def close(self) -> None:
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        listener = getattr(self, "listener", None)
        if listener is not None and listener.is_alive() and listener is not threading.current_thread():
            listener.join(timeout=0.5)
        backend = getattr(self, "_backend", None)
        try:
            if backend is not None:
                backend.stop_listening()
        finally:
            self.close_connection()

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self._backend.send(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        backend = getattr(self, "_backend", None)
        try:
            if backend is not None:
                backend.close_connection()
        finally:
            if getattr(self, "_multicast_sender", None) is not None and self._multicast_sender.enabled:
                self.disable_multicast()

    @property
    def status(self) -> int:
        return self._backend.status

    @status.setter
    def status(self, value: int) -> None:
        self._backend.status = value

    @property
    def invalidSocket(self) -> bool:
        return self._backend.invalid_socket

    @property
    def sock(self) -> socket.socket | None:
        """Underlying Python socket of the active backend, if any.

        ``None`` for backends that are not based on a plain Python socket.
        Exposed for diagnostics/advanced use (e.g. ``examples/bryan_lieblick.py``,
        which wraps it to observe ``recvfrom()``).
        """
        return self._backend.sock

    @sock.setter
    def sock(self, value: socket.socket | None) -> None:
        self._backend.sock = value

    def on_framing_error(self, error: FramingError, offset: int) -> None:
        self.logger.error(f"Ethernet framing error: {error!s} at offset {offset}")

    # =========================================================================
    # XCP 1.5: GET_DAQ_CLOCK_MULTICAST Support
    # =========================================================================

    @staticmethod
    def cluster_id_to_multicast_address(cluster_id: int) -> str:
        """
        Convert CLUSTER_AFFILIATION to IPv4 multicast address.

        XCP 1.5 Spec: IPv4-Multicast-Addr = 239.255.HIGH_BYTE.LOW_BYTE

        Args:
            cluster_id: 16-bit cluster identifier (Intel byte order)

        Returns:
            IPv4 multicast address (e.g., "239.255.0.1" for cluster_id=0x0001)
        """
        return EthMulticastSender.address(cluster_id)

    def enable_multicast(self, cluster_id: int = 0x0001) -> None:
        """
        Enable UDP multicast for GET_DAQ_CLOCK_MULTICAST.

        Creates a separate UDP socket for sending multicast commands.
        Responses (EV_TIME_SYNC events) come back on the regular connection.
        The XCP cluster-address mapping is IPv4, independently of the main
        transport's address family.

        Args:
            cluster_id: CLUSTER_AFFILIATION parameter (default: 0x0001 → 239.255.0.1)
        """
        address = self.cluster_id_to_multicast_address(cluster_id)
        if self._multicast_sender.enabled:
            self.logger.warning("Multicast already enabled")
            return

        if self.config.protocol.upper() != "UDP":
            self.logger.warning("GET_DAQ_CLOCK_MULTICAST requires UDP protocol (current: TCP)")
            # Still create the socket - it might work for mixed mode slaves

        self._multicast_sender.enable()
        self.logger.info(f"Multicast enabled: cluster_id={cluster_id:#06x} -> {address}:{DEFAULT_XCP_MULTICAST_PORT}")

    def disable_multicast(self) -> None:
        """Disable multicast and close the multicast socket."""
        self._multicast_sender.disable()
        self.logger.info("Multicast disabled")

    def send_multicast(self, cluster_id: int, counter: int) -> None:
        """
        Send GET_DAQ_CLOCK_MULTICAST command via UDP multicast.

        XCP 1.5 Spec:
        - Frame (ETH framing): [LEN:WORD][CTR:WORD][0xF2][0xFA][CLUSTER_ID:WORD][COUNTER:BYTE]
        - Port: 5557
        - Address: 239.255.HIGH_BYTE.LOW_BYTE (derived from cluster_id)
        - Response: Asynchronous EV_TIME_SYNC event on regular connection

        Args:
            cluster_id: 16-bit cluster identifier (Intel byte order)
            counter: 8-bit counter for consistency checks
        """
        multicast_addr = self.cluster_id_to_multicast_address(cluster_id)
        EthMulticastSender.validate_counter(counter)

        if not self._multicast_sender.enabled:
            # Auto-enable if not already enabled
            self.enable_multicast(cluster_id)

        if not self._multicast_sender.enabled:
            raise RuntimeError("Multicast socket not available")

        self._multicast_sender.send(self.framing, cluster_id, counter, DEFAULT_XCP_MULTICAST_PORT)
        self.logger.debug(
            f"GET_DAQ_CLOCK_MULTICAST sent: cluster={cluster_id:#06x}, counter={counter} -> "
            f"{multicast_addr}:{DEFAULT_XCP_MULTICAST_PORT}"
        )
