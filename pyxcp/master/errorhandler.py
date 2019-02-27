#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

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

import inspect
import functools

from pprint import pprint

from pyxcp.types import XcpResponseError, XcpTimeoutError
from pyxcp.errormatrix import ERROR_MATRIX, TIMEOUT, PreAction, Action

def getErrorHandler(service):
    return ERROR_MATRIX.get(service)

def getTimeoutHandler(service):
    handler = getErrorHandler(service)
    return handler.get(TIMEOUT)

def execute(inst, func, arguments):
    handler = Handler(inst, func, arguments)
    try:
        res = func(*arguments.args, **arguments.kwargs)
    except XcpResponseError as e:
        errorCode = XcpResponseError(e.args[0])
        handler.handleError(errorCode)
        raise
    except XcpTimeoutError as e:
        handler.handleTimeout()
        raise
    except Exception:
        raise
    else:
        return res

class Arguments:
    """Container for positional and keyword arguments.
    """
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


class Handler:

    def __init__(self, instance, func, args):
        self.instance = instance
        self.func = func
        self.args = args

    def handleError(self, errorCode):
        eh = getErrorHandler(self.service)

    def handleTimeout(self):
        preActions, actions = getTimeoutHandler(self.service)
        print("\tTOH", preActions, actions)
        self.doPreActions(preActions)
        self.doActions(actions)

    def doPreActions(self, preActions):
        """
            NONE
            WAIT_T7
            SYNCH
            GET_SEED_UNLOCK
            SET_MTA
            SET_DAQ_PTR
            START_STOP_X
            REINIT_DAQ
            DISPLAY_ERROR
            DOWNLOAD
            PROGRAM
            UPLOAD
            UNLOCK_SLAVE
        """
        if isinstance(preActions, (tuple, list)):
            for item in preActions:
                print("\t", item)
                self.doPreAction(item)
        else:
            self.doPreAction(preActions)

    def doPreAction(self, preAction):
        if preAction == PreAction.NONE:
            print("\t\tNOP")

    def doActions(self, actions):
        if isinstance(actions, (tuple, list)):
            for item in actions:
                print("\t", item)
                self.doAction(item)
        else:
            self.doAction(actions)


    def doAction(self, action):
        """
            NONE
            DISPLAY_ERROR
            RETRY_SYNTAX
            RETRY_PARAM
            USE_A2L
            USE_ALTERATIVE
            REPEAT
            REPEAT_2_TIMES
            REPEAT_INF_TIMES
            RESTART_SESSION
            TERMINATE_SESSION
            SKIP
            NEW_FLASH_WARE
        """
        #print("ACTION", action)
        if action in (Action.NONE, Action.SKIP):
            print("\t\tNOP")
        elif action == Action.REPEAT_INF_TIMES:
            print("\tREPEAT_INF_TIMES", self.func)

    @property
    def service(self):
        return self.instance.service


def wrapped(func):
    """WIP: This decorator will do XCP error-handling.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        inst = args[0] # First parameter is 'self'.
        arguments = Arguments(args, kwargs)
        handler = Handler(inst, func, arguments)
        return execute(inst, func, arguments)
    return inner
