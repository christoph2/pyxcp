#!/usr/bin/env python
"""Implements error-handling according to XCP spec."""

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

# Thread-local flag to suppress logging for expected XCP negative responses


_thread_flags = threading.local()


def set_suppress_xcp_error_log(value: bool) -> None:
    try:
        _thread_flags.suppress_xcp_error_log = bool(value)
    except Exception:
        pass


def is_suppress_xcp_error_log() -> bool:
    try:
        return bool(getattr(_thread_flags, "suppress_xcp_error_log", False))
    except Exception:
        return False


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

    def _diagnostics_enabled(self) -> bool:
        try:
            app = getattr(self.instance, "config", None)
            if app is None:
                return True
            general = getattr(app, "general", None)
            if general is None:
                return True
            return bool(getattr(general, "diagnostics_on_failure", True))
        except Exception:
            return True

    def _build_transport_diagnostics(self) -> str:
        try:
            transport = getattr(self.instance, "transport", None)
            if transport is None:
                return ""
            if hasattr(transport, "_build_diagnostics_dump"):
                return transport._build_diagnostics_dump()  # type: ignore[attr-defined]
        except Exception:
            pass
        return ""

    def _append_diag(self, msg: str) -> str:
        # Suppress diagnostics entirely when XCP error logging is suppressed (e.g., try_command probing)
        if is_suppress_xcp_error_log():
            return msg
        if not self._diagnostics_enabled():
            return msg
        diag = self._build_transport_diagnostics()
        if not diag:
            return msg
        # Prefer a Rich-formatted table for compact, readable diagnostics.
        try:
            header = "--- Diagnostics (for troubleshooting) ---"
            body = diag
            if "\n" in diag and diag.startswith("--- Diagnostics"):
                header, body = diag.split("\n", 1)

            # Try to parse the structured JSON body produced by transports
            import json as _json  # Local import to avoid hard dependency at module import time

            payload = _json.loads(body)
            transport_params = payload.get("transport_params") or {}
            last_pdus = payload.get("last_pdus") or []

            # Try to use rich if available
            try:
                from rich.console import Console
                from rich.table import Table
                from rich.panel import Panel
                from textwrap import shorten

                console = Console(file=None, force_terminal=False, width=120, record=True, markup=False)

                # Transport parameters table
                tp_table = Table(title="Transport Parameters", title_style="bold", show_header=True, header_style="bold magenta")
                tp_table.add_column("Key", style="cyan", no_wrap=True)
                tp_table.add_column("Value", style="white")
                from rich.markup import escape as _escape

                for k, v in (transport_params or {}).items():
                    # Convert complex values to compact repr
                    sv = repr(v)
                    sv = shorten(sv, width=80, placeholder="…")
                    tp_table.add_row(_escape(str(k)), _escape(sv))

                # Last PDUs table (most recent last)
                pdu_table = Table(
                    title="Last PDUs (most recent last)", title_style="bold", show_header=True, header_style="bold magenta"
                )
                for col in ("dir", "cat", "ctr", "ts", "len", "data"):
                    pdu_table.add_column(col, no_wrap=(col in {"dir", "cat", "ctr", "len"}), style="white")
                for pdu in last_pdus:
                    try:
                        dir_ = str(pdu.get("dir", ""))
                        cat = str(pdu.get("cat", ""))
                        ctr = str(pdu.get("ctr", ""))
                        # Format timestamp: convert ns -> s with 5 decimals if numeric
                        ts_val = pdu.get("ts", "")
                        try:
                            ts_num = int(ts_val)
                            ts = f"{ts_num / 1_000_000_000:.5f}"
                        except Exception:
                            ts = str(ts_val)
                        ln = str(pdu.get("len", ""))
                        # Prefer showing actual data content; avoid repr quotes
                        data_val = pdu.get("data", "")
                        try:
                            if isinstance(data_val, (bytes, bytearray, list, tuple)):
                                # Lazily import to avoid hard dependency
                                from pyxcp.utils import hexDump as _hexDump

                                data_str = _hexDump(data_val)
                            else:
                                data_str = str(data_val)
                        except Exception:
                            data_str = str(data_val)
                        # Shorten potentially huge values to keep table compact
                        from textwrap import shorten as _shorten

                        ts = _shorten(ts, width=20, placeholder="…")
                        data = _shorten(data_str, width=40, placeholder="…")
                        # Escape strings to avoid Rich markup interpretation (e.g., '[' ']' in hex dumps)
                        dir_e = _escape(dir_)
                        cat_e = _escape(cat)
                        ctr_e = _escape(ctr)
                        ts_e = _escape(ts)
                        ln_e = _escape(ln)
                        data_e = _escape(data)
                        pdu_table.add_row(dir_e, cat_e, ctr_e, ts_e, ln_e, data_e)
                    except Exception:
                        # If anything odd in structure, add a single-cell row with repr
                        from textwrap import shorten as _shorten

                        pdu_table.add_row(_shorten(repr(pdu), width=80, placeholder="…"), "", "", "", "", "")

                # Combine into a single panel and capture as text
                console.print(Panel.fit(tp_table, title=header))
                if last_pdus:
                    console.print(pdu_table)
                rendered = console.export_text(clear=False)

            except Exception:
                # Rich not available or rendering failed; fallback to compact logger lines
                self.logger.error(header)
                if transport_params:
                    self.logger.error("transport_params: %s", transport_params)
                if last_pdus:
                    self.logger.error("last_pdus (most recent last):")
                    for pdu in last_pdus:
                        try:
                            ts_val = pdu.get("ts", "")
                            try:
                                ts_num = int(ts_val)
                                ts_fmt = f"{ts_num / 1_000_000_000:.5f}"
                            except Exception:
                                ts_fmt = str(ts_val)
                            data_val = pdu.get("data", "")
                            if isinstance(data_val, (bytes, bytearray, list, tuple)):
                                from pyxcp.utils import hexDump as _hexDump

                                data_str = _hexDump(data_val)
                            else:
                                data_str = str(data_val)
                            pdu_copy = dict(pdu)
                            pdu_copy["ts"] = ts_fmt
                            pdu_copy["data"] = data_str
                            self.logger.error("%s", pdu_copy)
                        except Exception:
                            self.logger.error("%s", pdu)
        except Exception:
            # As a last resort, emit the whole diagnostics blob verbatim
            try:
                for line in diag.splitlines():
                    self.logger.error(line)
            except Exception:
                pass
        return msg

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
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (DISPLAY_ERROR)."), self.error_code)
            elif item == Action.RETRY_SYNTAX:
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (RETRY_SYNTAX)."), self.error_code)
            elif item == Action.RETRY_PARAM:
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (RETRY_PARAM)."), self.error_code)
            elif item == Action.USE_A2L:
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (USE_A2L)."), self.error_code)
            elif item == Action.USE_ALTERATIVE:
                raise SystemExit(
                    self._append_diag("Could not proceed due to unhandled error (USE_ALTERATIVE)."), self.error_code
                )  # TODO: check alternatives.
            elif item == Action.REPEAT:
                repetitionCount = Repeater.REPEAT
            elif item == Action.REPEAT_2_TIMES:
                repetitionCount = Repeater.REPEAT_2_TIMES
            elif item == Action.REPEAT_INF_TIMES:
                repetitionCount = Repeater.INFINITE
            elif item == Action.RESTART_SESSION:
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (RESTART_SESSION)."), self.error_code)
            elif item == Action.TERMINATE_SESSION:
                raise SystemExit(
                    self._append_diag("Could not proceed due to unhandled error (TERMINATE_SESSION)."), self.error_code
                )
            elif item == Action.SKIP:
                pass
            elif item == Action.NEW_FLASH_WARE:
                raise SystemExit(self._append_diag("Could not proceed due to unhandled error (NEW_FLASH_WARE)"), self.error_code)
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
                    try:
                        svc = getattr(inst.service, "name", None)
                        # Derive a human-friendly error name if available
                        try:
                            err_name = (
                                getattr(XcpError, int(self.error_code)).name
                                if hasattr(XcpError, "__members__")
                                else str(self.error_code)
                            )
                        except Exception:
                            # Fallbacks: try enum-style .name or string conversion
                            err_name = getattr(self.error_code, "name", None) or str(self.error_code)
                        try:
                            err_code_int = int(self.error_code)
                        except Exception:
                            err_code_int = self.error_code  # best effort
                        msg = f"XCP negative response: {err_name} (0x{err_code_int:02X})"
                        if svc:
                            msg += f" on service {svc}"
                        # Suppress noisy ERROR log if requested by caller context
                        if is_suppress_xcp_error_log():
                            self.logger.debug(
                                msg,
                                extra={
                                    "event": "xcp_error_suppressed",
                                    "service": svc,
                                    "error_code": err_code_int,
                                    "error_name": err_name,
                                },
                            )
                        else:
                            self.logger.error(
                                msg,
                                extra={
                                    "event": "xcp_error",
                                    "service": svc,
                                    "error_code": err_code_int,
                                    "error_name": err_name,
                                },
                            )
                    except Exception:
                        pass
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
                        msg = f"Max. repetition count reached while trying to execute service {handler.func.__name__!r}."
                        # Try to append diagnostics from the transport
                        try:
                            if hasattr(handler, "_append_diag"):
                                msg = handler._append_diag(msg)
                        except Exception:
                            pass
                        try:
                            self.logger.error(
                                "XCP unrecoverable",
                                extra={"event": "xcp_unrecoverable", "service": getattr(inst.service, "name", None)},
                            )
                        except Exception:
                            pass
                        raise UnrecoverableError(msg)
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
