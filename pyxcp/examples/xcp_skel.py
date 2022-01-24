#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use this as a copy-and-paste template for your own scripts.
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2020 by Christoph Schueler <cpu12.gems@googlemail.com>

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


def callout(master, args):
    if args.sk_dll:
        master.seedNKeyDLL = args.sk_dll


ap = ArgumentParser(description="pyXCP skeleton.", callout=callout)

# Add command-line option for seed-and-key DLL.
ap.parser.add_argument(
    "-s",
    "--sk-dll",
    dest="sk_dll",
    help="Seed-and-Key .DLL name",
    type=str,
    default=None,
)

with ap.run() as x:
    x.connect()
    if x.slaveProperties.optionalCommMode:
        # Collect additional properties.
        x.getCommModeInfo()

    # getId() is not strictly required.
    gid = x.getId(0x1)
    slave_name = x.fetch(gid.length)

    # Unlock resources, if necessary.
    # Could be more specific, like cond_unlock("DAQ")
    # Note: Unlocking requires a seed-and-key DLL.
    x.cond_unlock()

    ##
    # Your own code goes here.
    ##

    x.disconnect()

# Print some useful information.
# print("\nSlave properties:")
# print("=================")
# print("ID: '{}'".format(slave_name.decode("utf8")))
# pprint(x.slaveProperties)
