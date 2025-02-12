#!/usr/bin/env python
"""Implements error-handling according to XCP spec.
"""
import functools
import logging
import threading
import time
import types
from collections import namedtuple
from typing import Generic, List, Optional, TypeVar

import can

from pyxcp.errormatrix import ERROR_MATRIX, Action, PreAction
from pyxcp.types import COMMAND_CATEGORIES, XcpError, XcpResponseError, XcpTimeoutError


handle_errors = True  # enable/disable XCP error-handling.


class SingletonBase:
    _lock = threading.Lock()

    def __new__(cls, *args, **kws):
        # Double-Checked Locking
        if not hasattr(cls, "_instance"):
            try:
                cls._lock.acquire()
                if not hasattr(cls, "_instance"):
                    cls._instance = super().__new__(cls)
            finally:
                cls._lock.release()
        return cls._instance


Function = namedtuple("Function", "fun arguments")  # store: var | load: var


class InternalError(Exception):
    """Indicates an internal error, like invalid service."""


class SystemExit(Exception):
    """"""

    def __init__(self, msg: str, error_code: int = None, *args, **kws):
        super().__init__(*args, **kws)
        self.error_code = error_code
        self.msg = msg

    def __str__(self):
        return f"SystemExit(error_code={self.error_code}, message={self.msg!r})"

    __repr__ = __str__


class UnrecoverableError(Exception):
    """"""


def func_name(func):
    return func.__qualname__ if func is not None else None


def getErrorHandler(service):
    """"""
    return ERROR_MATRIX.get(service)


def getTimeoutHandler(service):
    """"""
    handler = getErrorHandler(service)
    if handler is None:
        raise InternalError("Invalid Service")
    return handler.get(XcpError.ERR_TIMEOUT)


def getActions(service, error_code):
    """"""
    error_str = str(error_code)
    if error_code == XcpError.ERR_TIMEOUT:
        preActions, actions = getTimeoutHandler(service)
    else:
        eh = getErrorHandler(service)
        if eh is None:
            raise InternalError(f"Invalid Service 0x{service:02x}")
        # print(f"Try to handle error -- Service: {service.name} Error-Code: {error_code}")
        handler = eh.get(error_str)
        if handler is None:
            raise SystemExit(f"Service {service.name!r} has no handler for {error_code}.", error_code=error_code)
        preActions, actions = handler
    return preActions, actions


def actionIter(actions):
    """Iterate over action from :file:`errormatrix.py`"""
    if isinstance(actions, (tuple, list)):
        yield from actions
    else:
        yield actions


class Arguments:
    """Container for positional and keyword arguments.

    Parameters
    ----------
        args: tuple
            Positional arguments
        kwargs: dict
            Keyword arguments.
    """

    def __init__(self, args=None, kwargs=None):
        if args is None:
            self.args = ()
        else:
            if not hasattr(args, "__iter__"):
                self.args = (args,)
            else:
                self.args = tuple(args)
        self.kwargs = kwargs or {}

    def __str__(self) -> str:
        res = f"{self.__class__.__name__}(ARGS = {self.args}, KWS = {self.kwargs})"
        return res

    def __eq__(self, other) -> bool:
        return (self.args == other.args if other is not None else False) and (
            self.kwargs == other.kwargs if other is not None else False
        )

    __repr__ = __str__


class Repeater:
    """A required action of some XCP errorhandler is repetition.

    Parameters
    ----------
        initial_value: int
            The actual values are predetermined by XCP:
                - REPEAT (one time)
                - REPEAT_2_TIMES (two times)
                - REPEAT_INF_TIMES ("forever")
    """

    REPEAT = 1
    REPEAT_2_TIMES = 2
    INFINITE = -1

    def __init__(self, initial_value: int):
        self._counter = initial_value
        # print("\tREPEATER ctor", hex(id(self)))

    def repeat(self):
        """Check if repetition is required.

        Returns
        -------
            bool
        """
        # print("\t\tCOUNTER:", hex(id(self)), self._counter)
        if self._counter == Repeater.INFINITE:
            return True
        elif self._counter > 0:
            self._counter -= 1
            return True
        else:
            return False


def display_error():
    """Display error information.

    TODO: callback.

    """


class Handler:
    """"""

    def __init__(self, instance, func, arguments, error_code=None):
        self.instance = instance
        if hasattr(func, "__closure__") and func.__closure__:
            self.func = func.__closure__[0].cell_contents  # Use original, undecorated function to prevent
            # nasty recursion problems.
        else:
            self.func = func
        self.arguments = arguments
        self.service = self.instance.service
        self._error_code: int = 0
        if error_code is not None:
            self._error_code = error_code
        self._repeater = None
        self.logger = logging.getLogger("PyXCP")

    def __str__(self):
        return f"Handler(func = {func_name(self.func)} -- {self.arguments} service = {self.service} error_code = {self.error_code})"

    def __eq__(self, other):
        if other is None:
            return False
        return (self.instance == other.instance) and (self.func == other.func) and (self.arguments == other.arguments)

    @property
    def error_code(self) -> int:
        return self._error_code

    @error_code.setter
    def error_code(self, value: int) -> None:
        self._error_code = value

    @property
    def repeater(self):
        # print("\tGet repeater", hex(id(self._repeater)), self._repeater is None)
        return self._repeater

    @repeater.setter
    def repeater(self, value):
        # print("\tSet repeater", hex(id(value)))
        self._repeater = value

    def execute(self):
        self.logger.debug(f"Execute({func_name(self.func)} -- {self.arguments})")
        if isinstance(self.func, types.MethodType):
            return self.func(*self.arguments.args, **self.arguments.kwargs)
        else:
            return self.func(self.instance, *self.arguments.args, **self.arguments.kwargs)

    def actions(self, preActions, actions):
        """Preprocess errorhandling pre-actions and actions."""
        result_pre_actions = []
        result_actions = []
        repetitionCount = 0
        for item in actionIter(preActions):
            if item == PreAction.NONE:
                pass
            elif item == PreAction.WAIT_T7:
                time.sleep(0.02)  # Completely arbitrary for now.
            elif item == PreAction.SYNCH:
                fn = Function(self.instance.synch, Arguments())
                result_pre_actions.append(fn)
            elif item == PreAction.GET_SEED_UNLOCK:
                raise NotImplementedError("Pre-action GET_SEED_UNLOCK")
            elif item == PreAction.SET_MTA:
                fn = Function(self.instance.setMta, Arguments(self.instance.mta))
                result_pre_actions.append(fn)
            elif item == PreAction.SET_DAQ_PTR:
                fn = Function(self.instance.setDaqPtr, Arguments(self.instance.currentDaqPtr))
            elif item == PreAction.START_STOP_X:
                raise NotImplementedError("Pre-action START_STOP_X")
            elif item == PreAction.REINIT_DAQ:
                raise NotImplementedError("Pre-action REINIT_DAQ")
            elif item == PreAction.DISPLAY_ERROR:
                pass
            elif item == PreAction.DOWNLOAD:
                raise NotImplementedError("Pre-action DOWNLOAD")
            elif item == PreAction.PROGRAM:
                raise NotImplementedError("Pre-action PROGRAM")
            elif item == PreAction.UPLOAD:
                raise NotImplementedError("Pre-action UPLOAD")
            elif item == PreAction.UNLOCK_SLAVE:
                resource = COMMAND_CATEGORIES.get(self.instance.service)  # noqa: F841
                raise NotImplementedError("Pre-action UNLOCK_SLAVE")
        for item in actionIter(actions):
            if item == Action.NONE:
                pass
            elif item == Action.DISPLAY_ERROR:
                raise SystemExit("Could not proceed due to unhandled error (DISPLAY_ERROR).", self.error_code)
            elif item == Action.RETRY_SYNTAX:
                raise SystemExit("Could not proceed due to unhandled error (RETRY_SYNTAX).", self.error_code)
            elif item == Action.RETRY_PARAM:
                raise SystemExit("Could not proceed due to unhandled error (RETRY_PARAM).", self.error_code)
            elif item == Action.USE_A2L:
                raise SystemExit("Could not proceed due to unhandled error (USE_A2L).", self.error_code)
            elif item == Action.USE_ALTERATIVE:
                raise SystemExit(
                    "Could not proceed due to unhandled error (USE_ALTERATIVE).", self.error_code
                )  # TODO: check alternatives.
            elif item == Action.REPEAT:
                repetitionCount = Repeater.REPEAT
            elif item == Action.REPEAT_2_TIMES:
                repetitionCount = Repeater.REPEAT_2_TIMES
            elif item == Action.REPEAT_INF_TIMES:
                repetitionCount = Repeater.INFINITE
            elif item == Action.RESTART_SESSION:
                raise SystemExit("Could not proceed due to unhandled error (RESTART_SESSION).", self.error_code)
            elif item == Action.TERMINATE_SESSION:
                raise SystemExit("Could not proceed due to unhandled error (TERMINATE_SESSION).", self.error_code)
            elif item == Action.SKIP:
                pass
            elif item == Action.NEW_FLASH_WARE:
                raise SystemExit("Could not proceed due to unhandled error (NEW_FLASH_WARE)", self.error_code)
        return result_pre_actions, result_actions, Repeater(repetitionCount)


T = TypeVar("T")


class HandlerStack(Generic[T]):
    """"""

    def __init__(self) -> None:
        self._stack: List[T] = []

    def push(self, value: T):
        if value != self.tos():
            self._stack.append(value)

    def pop(self) -> None:
        if len(self) > 0:
            self._stack.pop()

    def tos(self) -> Optional[T]:
        if len(self) > 0:
            return self._stack[-1]
        else:
            return None
            # raise ValueError("empty stack.")

    def empty(self) -> bool:
        return self._stack == []

    def __len__(self) -> int:
        return len(self._stack)

    def __repr__(self) -> str:
        result = []
        for idx in range(len(self)):
            result.append(str(self[idx]))
        return "\n".join(result)

    def __getitem__(self, ndx: int) -> T:
        return self._stack[ndx]

    __str__ = __repr__


class Executor(SingletonBase):
    """"""

    def __init__(self):
        self.handlerStack = HandlerStack()
        self.repeater = None
        self.logger = logging.getLogger("PyXCP")
        self.previous_error_code = None
        self.error_code = None
        self.func = None
        self.arguments = None

    def __call__(self, inst, func, arguments):
        self.inst = inst
        self.func = func
        self.arguments = arguments
        handler = Handler(inst, func, arguments)
        self.handlerStack.push(handler)
        connect_retries = inst.config.connect_retries
        try:
            while True:
                try:
                    handler = self.handlerStack.tos()
                    res = handler.execute()
                except XcpResponseError as e:
                    # self.logger.critical(f"XcpResponseError [{e.get_error_code()}]")
                    self.error_code = e.get_error_code()
                    handler.error_code = self.error_code
                except XcpTimeoutError:
                    is_connect = func.__name__ == "connect"
                    self.logger.warning(f"XcpTimeoutError -- Service: {func.__name__!r}")
                    self.error_code = XcpError.ERR_TIMEOUT
                    handler.error_code = self.error_code
                    if is_connect and connect_retries is not None:
                        if connect_retries == 0:
                            raise XcpTimeoutError("Maximum CONNECT retries reached.")
                        connect_retries -= 1
                except TimeoutError:
                    raise
                except can.CanError:
                    # self.logger.critical(f"Exception raised by Python CAN [{str(e)}]")
                    raise
                except Exception:
                    # self.logger.critical(f"Exception [{str(e)}]")
                    raise
                else:
                    self.error_code = None
                    self.handlerStack.pop()
                    if self.handlerStack.empty():
                        return res

                if self.error_code == XcpError.ERR_CMD_SYNCH:
                    # Don't care about SYNCH for now...
                    self.inst.logger.info("SYNCH received.")
                    continue

                if self.error_code is not None:
                    preActions, actions, repeater = handler.actions(*getActions(inst.service, self.error_code))
                    if handler.repeater is None:
                        handler.repeater = repeater
                    for f, a in reversed(preActions):
                        self.handlerStack.push(Handler(inst, f, a, self.error_code))
                self.previous_error_code = self.error_code
                if handler.repeater:
                    if handler.repeater.repeat():
                        continue
                    else:
                        raise UnrecoverableError(
                            f"Max. repetition count reached while trying to execute service {handler.func.__name__!r}."
                        )
        finally:
            # cleanup of class variables
            self.previous_error_code = None
            while not self.handlerStack.empty():
                self.handlerStack.pop()
            self.error_code = None
            self.func = None
            self.arguments = None


def disable_error_handling(value: bool):
    """Disable XCP error-handling (mainly for performance reasons)."""

    global handle_errors
    handle_errors = not bool(value)


def wrapped(func):
    """This decorator is XCP error-handling enabled."""

    @functools.wraps(func)
    def inner(*args, **kwargs):
        if handle_errors:
            inst = args[0]  # First parameter is 'self'.
            arguments = Arguments(args[1:], kwargs)
            executor = Executor()
            res = executor(inst, func, arguments)
        else:
            res = func(*args, **kwargs)
        return res

    return inner
