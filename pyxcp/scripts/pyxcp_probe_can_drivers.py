#!/usr/bin/env python

import can


def main():
    can.log.setLevel("ERROR")
    interfaces = can.detect_available_configs()
    print("-" * 80)
    if not interfaces:
        print("No CAN-interfaces installed on your system.")
    else:
        print("\nInstalled CAN-interfaces on your system:\n")
        interfaces = sorted(interfaces, key=lambda e: e["interface"])
        for interface in interfaces:
            print("\t{:20s} -- CHANNEL: {}".format(interface["interface"], interface["channel"]))


if __name__ == "__main__":
    main()
