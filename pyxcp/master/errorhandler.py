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
import time

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
        errorCode = e.args[0]
        # try to get a response in the error handler.
        res = handler.handleError(errorCode)
        if res is None:
            # None means response could not be retreived in the error handler,
            # so raise the pending error.
            raise
        else:
            # a response could be retreived in the error handler, hurray, return with that.
            return res
    except XcpTimeoutError as e:
        # try to get a response in the timeout handler.
        res = handler.handleTimeout()
        if res is None:
            # None means response could not be retreived in the timeout handler,
            # so raise the pending error.
            raise
        else:
            # a response could be retreived in the timeout handler, hurray, return with that.
            return res
    except Exception:
        # raise any other exceptions
        raise
    else:
        # return with the successfully received response
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
        if errorCode == 'ERR_GENERIC':
            preActions = PreAction.NONE
            actions = Action.DISPLAY_ERROR
        else:
            preActions, actions = eh.get(errorCode)
        print(f"\tEH (service: {self.service})", preActions, actions)
        # do not do the actions for error, we prefer to raise exception at once.
        # therefore, return None, indicating to raise the pending exception.
        return None
        # todo: uncomment the following lines, if error actions to be performed:
        # self.doPreActions(preActions)
        # res = self.doActions(actions)
        # return res

    def handleTimeout(self):
        preActions, actions = getTimeoutHandler(self.service)
        print("\tTOH", preActions, actions)
        # actually do the actions for timeout:
        immediate_error = self.doPreActions(preActions)
        if immediate_error:
            # return None, to force raising of the pending exception
            return None
        res = self.doActions(actions)
        return res

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
                immediate_error = self.doPreAction(item)
                if immediate_error:
                    break
        else:
            immediate_error = self.doPreAction(preActions)
        return immediate_error

    def doPreAction(self, preAction):
        immediate_error = False
        if preAction == PreAction.NONE:
            # print("\t\tNOP")
            pass
        elif preAction == PreAction.SYNCH:
            self.instance.synch()
        elif preAction == PreAction.WAIT_T7:
            # todo: get T7 from A2L?
            T7 = 1
            time.sleep(T7)
        elif preAction == PreAction.DISPLAY_ERROR:
            immediate_error = True
        else:
            # todo: implement other preactions.
            # for now, raise pending error immediately for unhandled cases.
            immediate_error = True
        return immediate_error

    def doActions(self, actions):
        if isinstance(actions, (tuple, list)):
            raise TypeError('Multiple error action!?! Should be only one!')
            # for item in actions:
            #     print("\t", item)
            #     res = self.doAction(item)
        else:
            res = self.doAction(actions)
            return res


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
        res = None
        _repeat_count_value = None
        if action in (Action.NONE, Action.SKIP):
            print("\t\tNOP")
        elif action == Action.REPEAT_INF_TIMES:
            print("\tREPEAT_INF_TIMES", self.func)
            # res = execute(self.instance, self.func, self.args)
            # infinite: well, let it be only 2 as well.
            _repeat_count_value = 2
        elif action == Action.REPEAT_2_TIMES:
            _repeat_count_value = 2
        elif action == Action.DISPLAY_ERROR:
            # return with None to raise the pending exception at once
            pass
        else:
            # todo: implement other actions
            # return with None, that will eventually raise the pending exception.
            pass

        if _repeat_count_value is not None:
            # action is some kind of repeat, do that,
            # and try to get a response by repeating the request

            print(f"\tREPEAT_{_repeat_count_value}_TIMES", self.func, self.instance, self.instance.repeat_counter)
            if self.instance.repeat_counter is None:
                self.instance.repeat_counter = _repeat_count_value
            if self.instance.repeat_counter > 0:
                print(f'REPEAT {_repeat_count_value - self.instance.repeat_counter + 1} / {_repeat_count_value}')
                if self.instance.repeat_counter == 0:
                    self.instance.repeat_counter = None
                else:
                    self.instance.repeat_counter -= 1
                    res = execute(self.instance, self.func, self.args)
        return res


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
