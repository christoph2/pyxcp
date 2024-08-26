#!/usr/bin/env python

MAP_NAMES = {
    1: "BorlandC 16 Bit",
    2: "M166",
    3: "Watcom",
    4: "HiTech HC05",
    6: "IEEE",
    7: "Cosmic",
    8: "SDS",
    9: "Fujitsu Softune 1(.mp1)",
    10: "GNU",
    11: "Keil 16x",
    12: "BorlandC 32 Bit",
    13: "Keil 16x (static)",
    14: "Keil 8051",
    15: "ISI",
    16: "Hiware HC12",
    17: "TI TMS470",
    18: "Archimedes",
    19: "COFF",
    20: "IAR",
    21: "VisualDSP",
    22: "GNU 16x",
    23: "GNU VxWorks",
    24: "GNU 68k",
    25: "DiabData",
    26: "VisualDSP DOS",
    27: "HEW SH7055",
    28: "Metrowerks",
    29: "Microsoft standard",
    30: "ELF/DWARF 16 Bit",
    31: "ELF/DWARF 32 Bit",
    32: "Fujitsu Softune 3..8(.mps)",
    33: "Microware Hawk",
    34: "TI C6711",
    35: "Hitachi H8S",
    36: "IAR HC12",
    37: "Greenhill Multi 2000",
    38: "LN308(MITSUBISHI) for M16C/80",
    39: "COFF settings auto detected",
    40: "NEC CC78K/0 v35",
    41: "Microsoft extended",
    42: "ICCAVR",
    43: "Omf96 (.m96)",
    44: "COFF/DWARF",
    45: "OMF96 Binary (Tasking C196)",
    46: "OMF166 Binary (Keil C166)",
    47: "Microware Hawk Plug&Play ASCII",
    48: "UBROF Binary (IAR)",
    49: "Renesas M32R/M32192 ASCII",
    50: "OMF251 Binary (Keil C251)",
    51: "Microsoft standard VC8",
    52: "Microsoft VC8 Release Build (MATLAB DLL)",
    53: "Microsoft VC8 Debug Build (MATLAB DLL)",
    54: "Microsoft VC8 Debug file (pdb)",
}

"""
3.0  Automatic detection sequence

-  The master (CANape) sends the command GET_ID with the idType = 219 (0xDB hex) to the ECU
-  The ECU sets the MTA (memory transfer address) pointer to the first byte of the data block containing the
MAP file identification and returns the number of bytes which need to be uploaded to the master as well as
the counter which defines the appropriate memory segment
-  The master requests the specified number of bytes from the ECU by sending UPLOAD commands
-  The master looks for the appropriate MAP file in the MAP file directory and updates the addresses in the
a2l file accordingly

Command sequence GET_ID

Id of the MAP format

Counter

MAP name

"""


def mapfile_name(name, counter, fmt):
    return f"{fmt:2d}{counter:d}{name:s}.map"
