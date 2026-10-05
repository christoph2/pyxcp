#!/usr/bin/env python
import socket
import struct

from pyxcp import types
from pyxcp.cpp_ext.cpp_ext import init_networking
from pyxcp.transport.eth_backend import EthIoBackend, create_eth_backend
from pyxcp.transport.transport_ext import EthProtocol, EthConfig, EthReceiver, FramingError

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
        eth_config.ptp_timestamping = self.config.ptp_timestamping
        address_to_bind: str = self.config.bind_to_address
        bind_to_port: int = self.config.bind_to_port
        eth_config.bind_to = (address_to_bind, bind_to_port) if address_to_bind else None

        # Initialized early so close_connection()/__del__ are safe even if
        # backend creation below fails (e.g. invalid/unavailable
        # experimental_backend selection).
        self._multicast_sock: socket.socket | None = None
        self._multicast_enabled = False

        init_networking()

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
        # Optimized: reduced from 2.0s to 0.5s timeout since listener now uses
        # 0.1s recv() timeout and should exit quickly when closeEvent is set
        try:
            if self.listener.is_alive():
                self.listener.join(timeout=0.5)
        except Exception:  # nosec
            pass  # Listener thread cleanup failure is non-critical
        self._backend.stop_listening()
        self.close_connection()

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self._backend.send(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        if not hasattr(self, "_backend"):
            # __init__ failed before the backend was created (e.g. invalid/
            # unavailable experimental_backend selection); nothing to close.
            return
        self._backend.close_connection()
        # XCP 1.5: Close multicast socket if enabled
        if self._multicast_enabled:
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
        high_byte = (cluster_id >> 8) & 0xFF
        low_byte = cluster_id & 0xFF
        return f"239.255.{high_byte}.{low_byte}"

    def enable_multicast(self, cluster_id: int = 0x0001) -> None:
        """
        Enable UDP multicast for GET_DAQ_CLOCK_MULTICAST.

        Creates a separate UDP socket for sending multicast commands.
        Responses (EV_TIME_SYNC events) come back on the regular connection.

        Args:
            cluster_id: CLUSTER_AFFILIATION parameter (default: 0x0001 → 239.255.0.1)
        """
        if self._multicast_enabled:
            self.logger.warning("Multicast already enabled")
            return

        if self.protocol != "UDP":
            self.logger.warning("GET_DAQ_CLOCK_MULTICAST requires UDP protocol (current: TCP)")
            # Still create the socket - it might work for mixed mode slaves

        try:
            # Create UDP socket for multicast transmission
            address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
            self._multicast_sock = socket.socket(address_family, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

            # Set TTL for multicast (site-local scope)
            if self.ipv6:
                # IPv6: Set multicast hop limit
                self._multicast_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 2)
            else:
                # IPv4: Set TTL
                self._multicast_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

            # Allow address reuse (multiple XCP masters on same host)
            self._multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                self._multicast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

            # Store multicast address
            self._multicast_address = self.cluster_id_to_multicast_address(cluster_id)
            self._multicast_port = DEFAULT_XCP_MULTICAST_PORT
            self._cluster_id = cluster_id

            self._multicast_enabled = True
            self.logger.info(f"Multicast enabled: cluster_id={cluster_id:#06x} → {self._multicast_address}:{self._multicast_port}")

        except Exception as e:
            self.logger.error(f"Failed to enable multicast: {e}", exc_info=True)
            if self._multicast_sock:
                self._multicast_sock.close()
                self._multicast_sock = None

    def disable_multicast(self) -> None:
        """Disable multicast and close the multicast socket."""
        if self._multicast_sock:
            try:
                self._multicast_sock.close()
            except Exception as e:  # nosec B110
                # Ignore errors during cleanup - socket may already be closed
                self.logger.debug(f"Error closing multicast socket (ignored): {e}")
            self._multicast_sock = None
        self._multicast_enabled = False
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
        if not self._multicast_enabled:
            # Auto-enable if not already enabled
            self.enable_multicast(cluster_id)

        if not self._multicast_sock:
            raise RuntimeError("Multicast socket not available")

        # Build GET_DAQ_CLOCK_MULTICAST packet with proper XCP framing
        # Transport Layer Command (0xF2) + Subcommand 0xFA + CLUSTER_ID (LE) + Counter (BYTE)
        cluster_id_le = cluster_id & 0xFFFF
        packet = self.framing.prepare_request(
            types.Command.TRANSPORT_LAYER_CMD,
            0xFA,
            cluster_id_le & 0xFF,
            (cluster_id_le >> 8) & 0xFF,
            counter & 0xFF,
        )

        # Send to multicast address
        multicast_addr = self.cluster_id_to_multicast_address(cluster_id)
        try:
            self._multicast_sock.sendto(packet, (multicast_addr, DEFAULT_XCP_MULTICAST_PORT))
            self.logger.debug(
                f"GET_DAQ_CLOCK_MULTICAST sent: cluster={cluster_id:#06x}, counter={counter} → "
                f"{multicast_addr}:{DEFAULT_XCP_MULTICAST_PORT}"
            )
        except Exception as e:
            self.logger.error(f"Failed to send multicast: {e}", exc_info=True)
            raise
