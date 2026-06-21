#!/usr/bin/env python
"""Discover XCP-on-Ethernet slaves via multicast."""

import argparse
import ipaddress
from pprint import pprint

from pyxcp.cmdline import ArgumentParser


def _parse_mac(value: str) -> bytes:
    text = value.replace(":", "").replace("-", "").replace(".", "")
    if len(text) != 12:
        raise argparse.ArgumentTypeError("MAC address must contain 6 bytes")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid MAC address: {value}") from exc


def _parse_ipv4(value: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid IPv4 address: {value}") from exc


def _print_responses(responses) -> None:
    if not responses:
        print("No XCP Ethernet slaves discovered.")
        return
    for index, response in enumerate(responses, 1):
        print(f"Response #{index}")
        pprint(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover XCP-on-Ethernet slaves via multicast.")
    parser.add_argument("--extended", action="store_true", help="Use GET_SLAVE_ID_EXTENDED.")
    parser.add_argument("--timeout", type=float, default=0.3, help="Response collection timeout in seconds.")
    parser.add_argument("--mode", type=int, default=0, help="Discovery mode byte.")
    parser.add_argument("--ip-version", type=int, default=0, choices=(0, 1), help="GET_SLAVE_ID IP version selector.")
    parser.add_argument("--dest-address", default="239.255.0.0", help="Multicast destination address.")
    parser.add_argument("--dest-port", type=int, default=5556, help="Multicast destination port.")
    parser.add_argument("--response-address", default="239.255.0.0", help="Multicast response group/address.")
    parser.add_argument("--response-port", type=int, default=5556, help="Response port.")
    parser.add_argument(
        "--set-ip",
        nargs=2,
        metavar=("MAC", "IP"),
        help="Assign IPv4 address to slave selected by MAC address.",
    )
    ap = ArgumentParser(parser)

    master = ap.run()
    try:
        if ap.args.set_ip:
            mac = _parse_mac(ap.args.set_ip[0])
            new_ip = _parse_ipv4(ap.args.set_ip[1])
            positives, negatives = master.setSlaveIpAddressEthernet(
                mac=mac,
                new_ip=new_ip,
                response_port=ap.args.response_port,
                response_address=ap.args.response_address,
                timeout=ap.args.timeout,
                mode=ap.args.mode,
                dest_address=ap.args.dest_address,
                dest_port=ap.args.dest_port,
            )
            print("Positive responses:")
            _print_responses(positives)
            print("Negative responses:")
            _print_responses(negatives)
        elif ap.args.extended:
            responses = master.getSlaveIdExtendedEthernet(
                response_port=ap.args.response_port,
                response_address=ap.args.response_address,
                timeout=ap.args.timeout,
                mode=ap.args.mode,
                dest_address=ap.args.dest_address,
                dest_port=ap.args.dest_port,
            )
            _print_responses(responses)
        else:
            responses = master.getSlaveIdEthernet(
                response_port=ap.args.response_port,
                response_address=ap.args.response_address,
                timeout=ap.args.timeout,
                ip_version=ap.args.ip_version,
                dest_address=ap.args.dest_address,
                dest_port=ap.args.dest_port,
            )
            _print_responses(responses)
    finally:
        master.close()


if __name__ == "__main__":
    main()
