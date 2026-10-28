#!/usr/bin/env python
"""Low-level I/O backends for the :class:`pyxcp.transport.eth.Eth` transport.

``Eth`` is responsible for XCP-level concerns (framing config, address
resolution parameters, multicast, timing) while the actual byte-level
network I/O (connect / send / receive-loop) is delegated to a native
:class:`EthIoBackend` implementation: IOCP on Windows, epoll on Linux and
kqueue on macOS and FreeBSD.

:class:`EthIoBackend` itself is the abstract C++ interface exposed by
``pyxcp.transport.transport_ext`` (``eth_io_backend.hpp``). It provides the
``eth``, ``logger`` and ``sock`` attributes and ``available = True``.
The C++ XCP framing/dispatch logic (``EthReceiver.feed_frame``) is shared by
every backend.
"""

import sys
from typing import TYPE_CHECKING

from pyxcp.transport.transport_ext import EthIoBackend

if TYPE_CHECKING:
    from pyxcp.transport.eth import Eth


class _UnavailableNativeBackend(EthIoBackend):
    """Stand-in used when the platform's native extension cannot be imported."""

    available = False


IocpSocketBackend: type[EthIoBackend] = _UnavailableNativeBackend
EpollSocketBackend: type[EthIoBackend] = _UnavailableNativeBackend
KqueueSocketBackend: type[EthIoBackend] = _UnavailableNativeBackend

if sys.platform == "win32":
    try:
        from pyxcp.transport.eth_ext import IocpBackend as IocpSocketBackend
    except ImportError:
        pass
elif sys.platform.startswith("linux"):
    try:
        from pyxcp.transport.eth_ext import EpollBackend as EpollSocketBackend
    except ImportError:
        pass
elif sys.platform == "darwin" or sys.platform.startswith("freebsd"):
    try:
        from pyxcp.transport.eth_ext import KqueueBackend as KqueueSocketBackend
    except ImportError:
        pass

_ETH_BACKENDS: dict[str, type[EthIoBackend]] = {
    "iocp": IocpSocketBackend,
    "epoll": EpollSocketBackend,
    "kqueue": KqueueSocketBackend,
}


def default_backend_name() -> str:
    """Name of the native backend for the current platform."""
    if sys.platform.startswith("linux"):
        return "epoll"
    if sys.platform == "darwin" or sys.platform.startswith("freebsd"):
        return "kqueue"
    return "iocp"


def create_eth_backend(name: str | None, eth: "Eth") -> EthIoBackend:
    """Factory for :class:`EthIoBackend` implementations.

    Parameters
    ----------
    name: str | None
        ``"iocp"`` (Windows), ``"epoll"`` (Linux) or ``"kqueue"`` (macOS/FreeBSD);
        ``None`` selects the backend of the current platform.
    eth: :class:`pyxcp.transport.eth.Eth`
        The owning transport instance.

    Raises
    ------
    ValueError
        If ``name`` is not a known backend.
    RuntimeError
        If the backend is not available on this platform/build.
    """
    if name is None:
        name = default_backend_name()
    key = name.lower()
    if key not in _ETH_BACKENDS:
        raise ValueError(f"{name!r} is an invalid Ethernet backend -- please choose one of [{' | '.join(_ETH_BACKENDS.keys())}].")
    backend_class = _ETH_BACKENDS[key]
    if not backend_class.available:
        raise RuntimeError(
            f"The {name!r} Ethernet backend is not available. Build the platform's native ``pyxcp.transport.eth_ext`` extension."
        )
    return backend_class(eth)
