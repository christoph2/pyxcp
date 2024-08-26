#!/usr/bin/env python

"""XCP info/exploration tool.
"""

from pprint import pprint

from pyxcp.cmdline import ArgumentParser
from pyxcp.types import TryCommandResult


def main():
    ap = ArgumentParser(description="XCP info/exploration tool.")

    with ap.run() as x:
        x.connect()
        if x.slaveProperties.optionalCommMode:
            x.try_command(x.getCommModeInfo, extra_msg="availability signaled by CONNECT, this may be a slave configuration error.")
        print("\nSlave Properties:")
        print("=================")
        pprint(x.slaveProperties)

        result = x.id_scanner()
        print("\n")
        print("Implemented IDs:")
        print("================")
        for key, value in result.items():
            print(f"{key}: {value}", end="\n\n")
        cps = x.getCurrentProtectionStatus()
        print("\nProtection Status")
        print("=================")
        for k, v in cps.items():
            print(f"    {k:6s}: {v}")
        x.cond_unlock()
        print("\nDAQ Info:")
        print("=========")
        daq_info = x.getDaqInfo()
        pprint(daq_info)

        daq_pro = daq_info["processor"]
        daq_properties = daq_pro["properties"]
        if x.slaveProperties.transport_layer == "CAN":
            print("")
            if daq_properties["pidOffSupported"]:
                print("*** pidOffSupported -- i.e. one CAN-ID per DAQ-list.")
            else:
                print("*** NO support for PID_OFF")
        num_predefined = daq_pro["minDaq"]
        print("\nPredefined DAQ-Lists")
        print("====================")
        if num_predefined > 0:
            print(f"There are {num_predefined} predefined DAQ-lists")
            for idx in range(num_predefined):
                print(f"DAQ-List #{idx}\n____________\n")
                status, dm = x.try_command(x.getDaqListMode, idx)
                if status == TryCommandResult.OK:
                    print(dm)
                status, di = x.try_command(x.getDaqListInfo, idx)
                if status == TryCommandResult.OK:
                    print(di)
        else:
            print("*** NO Predefined DAQ-Lists")
        print("\nPAG Info:")
        print("=========")
        if x.slaveProperties.supportsCalpag:
            status, pag = x.try_command(x.getPagProcessorInfo)
            if status == TryCommandResult.OK:
                print(pag)
                # for idx in range(pag.maxSegments):
                #     x.getSegmentInfo(0x01, idx, 0, 0)
        else:
            print("*** PAGING IS NOT SUPPORTED.")

        print("\nPGM Info:")
        print("=========")
        if x.slaveProperties.supportsPgm:
            status, pgm = x.try_command(x.getPgmProcessorInfo)
            if status == TryCommandResult.OK:
                print(pgm)
        else:
            print("*** FLASH PROGRAMMING IS NOT SUPPORTED.")

        if x.slaveProperties.transport_layer == "CAN":
            print("\nTransport-Layer CAN:")
            print("====================")
            status, res = x.try_command(x.getSlaveID, 0)
            if status == TryCommandResult.OK:
                print("CAN identifier for CMD/STIM:\n", res)
            else:
                print("*** GET_SLAVE_ID() IS NOT SUPPORTED.")  # no response from bc address ???

            print("\nPer DAQ-list Identifier")
            print("-----------------------")
            daq_id = 0
            while True:
                status, res = x.try_command(x.getDaqId, daq_id)
                if status == TryCommandResult.OK:
                    print(f"DAQ-list #{daq_id}:", res)
                    daq_id += 1
                else:
                    break
            if daq_id == 0:
                print("N/A")
        x.disconnect()
        print("\nDone.")


if __name__ == "__main__":
    main()
