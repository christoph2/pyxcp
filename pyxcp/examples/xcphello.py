#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Very basic hello-world example.
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2021 by Christoph Schueler <cpu12.gems@googlemail.com>

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


from pprint import pprint

from pyxcp.cmdline import ArgumentParser

daq_info = False


def callout(master, args):
    global daq_info
    if args.daq_info:
        daq_info = True


ap = ArgumentParser(description="pyXCP hello world.", callout=callout)
ap.parser.add_argument(
    "-d",
    "--daq-info",
    dest="daq_info",
    help="Display DAQ-info",
    default=False,
    action="store_true",
)
with ap.run() as x:
    x.connect()
    if x.slaveProperties.optionalCommMode:
        x.getCommModeInfo()
    gid = x.getId(0x1)
    result = x.fetch(gid.length)
    print("\nSlave properties:")
    print("=================")
    print("ID: '{}'".format(result.decode("utf8")))
    pprint(x.slaveProperties)

    if daq_info:
        dqp = x.getDaqProcessorInfo()
        print("\nDAQProcessor info:")
        print("==================")
        print(dqp)
        dqr = x.getDaqResolutionInfo()
        print("\nDAQResolution info:")
        print("===================")
        print(dqr)
        for idx in range(dqp.maxDaq):
            print("\nDAQList info #{}".format(idx))
            print("================")
            print("{}".format(x.getDaqListInfo(idx)))
    x.disconnect()
