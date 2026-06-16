#!/usr/bin/env python
"""
Discover XCP slaves on Ethernet via multicast and optionally assign a new IPv4 address.

Demonstrates:
- GET_SLAVE_ID (basic discovery)
- GET_SLAVE_ID_EXTENDED (adds MAC + identification types)
- SET_SLAVE_IP_ADDRESS (select by MAC, assign IPv4)

Defaults match the ASAM multicast group 239.255.0.0:5556.
"""

from __future__ import annotations

import argparse
import ipaddress
import logging
import socket
import struct
import time
from typing import Container, Iterable, Optional, Tuple

from pyxcp.transport.eth import (
    DEFAULT_XCP_DISCOVERY_ADDRESS,
    DEFAULT_XCP_DISCOVERY_PORT,
    DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
    DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
)

from pyxcp import types
from pyxcp.cpp_ext.cpp_ext import get_ipv4_interfaces

MAX_DATAGRAM_SIZE = 512

logger = logging.getLogger(__name__)


class XcpEthDiscovery:
    @staticmethod
    def _pack_ipv4_address(address: str) -> bytes:
        try:
            return socket.inet_aton(address)
        except OSError as exc:
            raise ValueError(f"Invalid IPv4 address: {address}") from exc

    @staticmethod
    def _unpack_header_and_payload(frame: bytes) -> tuple[int, bytes] | None:
        if len(frame) < 4:
            return None
        length = frame[0] | (frame[1] << 8)
        if len(frame) < 4 + length:
            return None
        counter = frame[2] | (frame[3] << 8)
        payload = frame[4 : 4 + length]
        return counter, payload

    def _parse_positive_payload(
        self,
        payload: bytes,
        parser,
        expected_subcommand: Optional[int] = None,
        framing: bool = True,
    ) -> Optional[Container]:
        if framing:
            if not payload:
                return None
            pid = payload[0]
            if pid != 0xFF:
                return None
            body = payload[1:]
            if expected_subcommand is not None and body and body[0] == expected_subcommand:
                body = body[1:]
        else:
            body = payload
        try:
            return parser.parse(body, byteOrder=types.ByteOrder.INTEL)
        except Exception:
            logger.debug("Failed to parse positive transport layer response", exc_info=True)
            return None

    def _parse_negative_payload(self, payload: bytes, expected_subcommand: int) -> Optional[Container]:
        if not payload or payload[0] != 0xFE:
            return None
        body = payload[1:]
        if body and body[0] == expected_subcommand:
            body = body[1:]
        try:
            return types.SetSlaveIpAddressNegativeResponse.parse(body, byteOrder=types.ByteOrder.INTEL)
        except Exception:
            try:
                return types.SetSlaveIpAddressNegativeResponse.parse(body)
            except Exception:
                self.logger.debug("Failed to parse negative transport layer response", exc_info=True)
                return None

    def get_slave_id_multicast(
        self,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        ip_version: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        """
        Send GET_SLAVE_ID (Ethernet multicast discovery).

        Returns a list of construct Containers parsed via types.GetSlaveIdEthResponse.
        """
        payload = bytearray()
        payload.append(types.TransportLayerCommands.GET_SLAVE_ID)
        payload.extend(struct.pack("<H", response_port))
        payload.extend(self._pack_ipv4_address(response_address))
        payload.extend(b"\x00" * 12)
        payload.append(ip_version & 0xFF)

        packet = self.frame_it(types.Command.TRANSPORT_LAYER_CMD, *payload)
        frames = self._multicast_send_receive(packet, dest_address, dest_port, response_address, response_port, timeout)
        results = []
        for addr, counter, raw_payload in frames:
            parsed = self._parse_positive_payload(raw_payload, types.GetSlaveIdEthResponse, framing=False)
            if parsed:
                parsed.source = addr
                parsed.counter = counter
                results.append(parsed)
        return results

    def _multicast_send_receive(
        self,
        packet: bytes,
        dest_address: str,
        dest_port: int,
        response_address: str,
        response_port: int,
        timeout: float,
    ) -> list[tuple[tuple[str, int], int, bytes]]:
        """
        Send a multicast packet and collect responses until timeout.

        Returns a list of tuples: (source_addr, counter, payload_with_pid)
        """
        results: list[tuple[tuple[str, int], int, bytes]] = []

        interfaces = get_ipv4_interfaces()
        for ifname, ip in interfaces:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            # Bind to response port to receive responses
            sock.bind(("", response_port))
            # Join multicast group for responses
            mreq = struct.pack("=4s4s", socket.inet_aton(response_address), socket.inet_aton("0.0.0.0"))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            # Limit multicast scope
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip))
            sock.settimeout(timeout)
            try:
                sock.sendto(packet, (dest_address, dest_port))
                end_time = time.monotonic() + timeout
                while True:
                    remaining = end_time - time.monotonic()
                    if remaining <= 0:
                        break
                    sock.settimeout(remaining)
                    try:
                        data, addr = sock.recvfrom(MAX_DATAGRAM_SIZE)
                    except socket.timeout:
                        break
                    parsed = self._unpack_header_and_payload(data)
                    if not parsed:
                        continue
                    counter, payload = parsed
                    results.append((addr, counter, payload))
                # return results
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
        return results

    def frame_it(self, cmd, *payload):
        length = struct.pack("<H", len(payload))
        counter = struct.pack("<H", 0)
        frame = length + counter + bytes([cmd]) + bytes(payload)
        return frame

    def get_slave_id_extended_multicast(
        self,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        mode: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        """
        Send GET_SLAVE_ID_EXTENDED (Ethernet multicast discovery).

        Returns a list of construct Containers parsed via types.GetSlaveIdExtendedResponse.
        """
        payload = bytearray()
        payload.append(types.TransportLayerCommands.GET_SLAVE_ID_EXTENDED)
        payload.extend(struct.pack("<H", response_port))
        payload.extend(self._pack_ipv4_address(response_address))
        payload.extend(b"\x00" * 12)
        payload.append(mode & 0xFF)
        packet = self.frame_it(types.Command.TRANSPORT_LAYER_CMD, *payload)
        frames = self._multicast_send_receive(packet, dest_address, dest_port, response_address, response_port, timeout)
        results = []
        for addr, counter, raw_payload in frames:
            parsed = self._parse_positive_payload(
                raw_payload,
                types.GetSlaveIdExtendedResponse,
                expected_subcommand=types.TransportLayerCommands.GET_SLAVE_ID_EXTENDED,
                framing=True,
            )
            if parsed:
                parsed.source = addr
                parsed.counter = counter
                results.append(parsed)
        return results

    def set_slave_ip_address(
        self,
        mac: bytes,
        new_ip: str,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        mode: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        """
        Send SET_SLAVE_IP_ADDRESS to assign a new IP to a slave selected by MAC address.

        Returns a tuple (positives, negatives) where each list contains parsed responses.
        """
        if len(mac) != 6:
            raise ValueError("MAC address must be exactly 6 bytes")

        payload = bytearray()
        payload.append(types.TransportLayerCommands.SET_SLAVE_IP_ADDRESS)
        payload.extend(struct.pack("<H", response_port))
        payload.extend(self._pack_ipv4_address(response_address))
        payload.extend(b"\x00" * 12)
        payload.append(mode & 0xFF)
        payload.extend(mac)
        payload.extend(self._pack_ipv4_address(new_ip))

        packet = self.frame_it(types.Command.TRANSPORT_LAYER_CMD, *payload)
        frames = self._multicast_send_receive(packet, dest_address, dest_port, response_address, response_port, timeout)
        positives = []
        negatives = []
        for addr, counter, raw_payload in frames:
            parsed_pos = self._parse_positive_payload(
                raw_payload, types.SetSlaveIpAddressResponse, expected_subcommand=types.TransportLayerCommands.SET_SLAVE_IP_ADDRESS
            )
            if parsed_pos:
                parsed_pos.source = addr
                parsed_pos.counter = counter
                positives.append(parsed_pos)
                continue
            parsed_neg = self._parse_negative_payload(
                raw_payload, expected_subcommand=types.TransportLayerCommands.SET_SLAVE_IP_ADDRESS
            )
            if parsed_neg:
                parsed_neg.source = addr
                parsed_neg.counter = counter
                negatives.append(parsed_neg)
        return positives, negatives

    def getSlaveIdEthernet(
        self,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        ip_version: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        """
        Discover slaves via GET_SLAVE_ID (Ethernet multicast).

        Returns list of parsed types.GetSlaveIdEthResponse containers (one per slave/port).
        """
        return self.get_slave_id_multicast(
            response_port=response_port,
            response_address=response_address,
            timeout=timeout,
            ip_version=ip_version,
            dest_address=dest_address,
            dest_port=dest_port,
        )

    def getSlaveIdExtendedEthernet(
        self,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        mode: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        """
        Discover slaves via GET_SLAVE_ID_EXTENDED (Ethernet multicast).

        Returns list of parsed types.GetSlaveIdExtendedResponse containers.
        """
        return self.get_slave_id_extended_multicast(
            response_port=response_port,
            response_address=response_address,
            timeout=timeout,
            mode=mode,
            dest_address=dest_address,
            dest_port=dest_port,
        )

    def setSlaveIpAddressEthernet(
        self,
        mac: bytes,
        new_ip: str,
        response_port: int = DEFAULT_XCP_DISCOVERY_RESPONSE_PORT,
        response_address: str = DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        timeout: float = 3.0,
        mode: int = 0,
        dest_address: str = DEFAULT_XCP_DISCOVERY_ADDRESS,
        dest_port: int = DEFAULT_XCP_DISCOVERY_PORT,
    ):
        return self.set_slave_ip_address(
            mac=mac,
            new_ip=new_ip,
            response_port=response_port,
            response_address=response_address,
            timeout=timeout,
            mode=mode,
            dest_address=dest_address,
            dest_port=dest_port,
        )

    def close(self):
        pass


def parse_mac(text: str) -> bytes:
    """Parse MAC strings like AA:BB:CC:DD:EE:FF or aabb.ccdd.eeff."""
    cleaned = text.replace("-", ":").replace(".", "")
    if ":" in cleaned:
        parts = cleaned.split(":")
    else:
        parts = [cleaned[i : i + 2] for i in range(0, len(cleaned), 2)]
    if len(parts) != 6:
        raise argparse.ArgumentTypeError("MAC must contain 6 octets (e.g. AA:BB:CC:DD:EE:FF)")
    try:
        return bytes(int(part, 16) for part in parts)
    except ValueError as exc:  # noqa: B904
        raise argparse.ArgumentTypeError(f"Invalid MAC segment in {text!r}") from exc


def format_ip(ip_bytes: bytes) -> str:
    return str(ipaddress.IPv4Address(ip_bytes))


def format_resource(resource) -> str:
    flags: Iterable[Tuple[str, bool]] = (
        ("DBG", resource.dbg),
        ("PGM", resource.pgm),
        ("STIM", resource.stim),
        ("DAQ", resource.daq),
        ("CALPAG", resource.calpag),
    )
    enabled = [name for name, enabled in flags if enabled]
    return ", ".join(enabled) if enabled else "NONE"


def format_protocol(status) -> str:
    value = 0
    if getattr(status, "ip_transport_protocol_i", False):
        value |= 1
    if getattr(status, "ip_transport_protocol_ii", False):
        value |= 2
    return {0: "TCP only", 1: "UDP only", 2: "TCP + UDP", 3: "reserved"}.get(value, "unknown")


def print_slave(label: str, resp) -> None:
    status = resp.status
    availability = "busy" if status.slv_availability else "free"
    ip_version = "IPv4" if not status.ip_version else "reserved"
    print(f"\n[{label}] {format_ip(resp.ip_address)}:{resp.port}")
    print(f"  status: {availability}, {ip_version}, {format_protocol(status)}")
    if hasattr(status, "slv_id_ext_supported"):
        print(f"  GET_SLAVE_ID_EXTENDED supported: {bool(status.slv_id_ext_supported)}")
    print(f"  resources: {format_resource(resp.resource)}")
    print(f"  identification ({resp.length} bytes): {resp.identification!r}")
    if hasattr(resp, "mac"):
        mac = ":".join(f"{b:02X}" for b in resp.mac)
        print(f"  mac: {mac}")
        if resp.remaining:
            print(f"  additional identification payload: {resp.remaining!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ethernet multicast discovery and IP assignment (pyXCP).")
    parser.add_argument("--host", default="0.0.0.0", help="Local host for transport init (not used for multicast).")
    parser.add_argument("--port", type=int, default=0, help="Local port for transport init (not used for multicast).")
    parser.add_argument(
        "--response-address",
        default=DEFAULT_XCP_DISCOVERY_RESPONSE_ADDRESS,
        help="Multicast address to listen on.",
    )
    parser.add_argument("--response-port", type=int, default=DEFAULT_XCP_DISCOVERY_RESPONSE_PORT, help="Port to listen on.")
    parser.add_argument("--dest-address", default=DEFAULT_XCP_DISCOVERY_ADDRESS, help="Destination multicast address.")
    parser.add_argument("--dest-port", type=int, default=DEFAULT_XCP_DISCOVERY_PORT, help="Destination multicast port.")
    parser.add_argument("--timeout", type=float, default=3.0, help="Receive timeout in seconds.")
    parser.add_argument("--extended", action="store_true", help="Also issue GET_SLAVE_ID_EXTENDED.")
    parser.add_argument("--set-ip", nargs=2, metavar=("MAC", "IP"), help="Send SET_SLAVE_IP_ADDRESS for the given MAC.")
    parser.add_argument("--mode", type=int, default=0, help="Mode/IP_VERSION bit for extended/set-ip commands (default: 0=IPv4).")
    args = parser.parse_args()

    master = XcpEthDiscovery()
    try:
        basic = master.getSlaveIdEthernet(
            response_port=args.response_port,
            response_address=args.response_address,
            timeout=args.timeout,
            ip_version=0,
            dest_address=args.dest_address,
            dest_port=args.dest_port,
        )
        if not basic:
            print("No GET_SLAVE_ID responses received.")
        for idx, resp in enumerate(basic, 1):
            print_slave(f"GET_SLAVE_ID #{idx}", resp)

        if args.extended:
            extended = master.getSlaveIdExtendedEthernet(
                response_port=args.response_port,
                response_address=args.response_address,
                timeout=args.timeout,
                mode=args.mode,
                dest_address=args.dest_address,
                dest_port=args.dest_port,
            )
            if not extended:
                print("\nNo GET_SLAVE_ID_EXTENDED responses received.")
            for idx, resp in enumerate(extended, 1):
                print_slave(f"GET_SLAVE_ID_EXTENDED #{idx}", resp)

        if args.set_ip:
            mac_bytes = parse_mac(args.set_ip[0])
            new_ip = str(ipaddress.IPv4Address(args.set_ip[1]))
            positives, negatives = master.setSlaveIpAddressEthernet(
                mac=mac_bytes,
                new_ip=new_ip,
                response_port=args.response_port,
                response_address=args.response_address,
                timeout=args.timeout,
                mode=args.mode,
                dest_address=args.dest_address,
                dest_port=args.dest_port,
            )
            print(f"\nSET_SLAVE_IP_ADDRESS: {len(positives)} positive, {len(negatives)} negative response(s)")
            for resp in positives:
                mac = ":".join(f"{b:02X}" for b in resp.mac)
                print(f"  ✓ status={resp.status} mac={mac}")
            for resp in negatives:
                mac = ":".join(f"{b:02X}" for b in resp.mac)
                print(f"  ✗ error={resp.errorCode} mac={mac}")
    finally:
        master.close()


if __name__ == "__main__":
    main()
