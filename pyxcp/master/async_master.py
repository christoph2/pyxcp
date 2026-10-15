#!/usr/bin/env python

import asyncio
import functools
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import Any
from collections.abc import Callable, Iterable

from pyxcp.transport.async_policy import AsyncFrameSubscription
from pyxcp.transport.transport_ext import FrameCategory

from .master import Master


class AsyncTransport:
    """Async facade for low-level transport access."""

    def __init__(self, owner: "AsyncMaster", transport: Any) -> None:
        self._owner = owner
        self._transport = transport

    @property
    def sync_transport(self) -> Any:
        return self._transport

    @property
    def policy(self) -> Any:
        return self._transport.policy

    def subscribe_frames(
        self,
        *,
        categories: Iterable[FrameCategory] | None = None,
        maxsize: int = 0,
    ) -> AsyncFrameSubscription:
        policy = self._transport.policy
        subscriber = getattr(policy, "subscribe", None)
        if not callable(subscriber):
            raise TypeError("Transport policy does not support async subscriptions. Use AsyncPolicyAdapter.")
        return subscriber(categories=categories, maxsize=maxsize)

    def subscribe_daq(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.subscribe_frames(categories={FrameCategory.DAQ}, maxsize=maxsize)

    def subscribe_events(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.subscribe_frames(categories={FrameCategory.EVENT}, maxsize=maxsize)

    def subscribe_responses(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.subscribe_frames(categories={FrameCategory.RESPONSE}, maxsize=maxsize)

    def subscribe_services(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.subscribe_frames(categories={FrameCategory.SERV}, maxsize=maxsize)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._transport, name)
        if callable(attr):
            return self._owner._wrap_callable(attr)
        return attr

    def __dir__(self) -> list[str]:
        return sorted(set(dir(type(self)) + dir(self._transport)))


class AsyncMaster:
    """Async facade around :class:`pyxcp.master.master.Master`.

    The adapter preserves the existing synchronous semantics by serializing all
    calls through a dedicated single-worker executor. This keeps the current
    request/response assumptions intact while exposing awaitable methods.
    """

    def __init__(
        self,
        master_or_transport: Any,
        config: Any = None,
        policy: Any = None,
        transport_layer_interface: Any = None,
        *,
        executor: Executor | None = None,
    ) -> None:
        if isinstance(master_or_transport, str):
            if config is None:
                raise ValueError("config must be provided when constructing AsyncMaster from transport name.")
            self._master = Master(
                master_or_transport,
                config=config,
                policy=policy,
                transport_layer_interface=transport_layer_interface,
            )
        elif config is not None or policy is not None or transport_layer_interface is not None:
            raise ValueError("config, policy and transport_layer_interface are only valid with a transport name.")
        else:
            self._master = master_or_transport

        self._executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="pyxcp-async-master")
        self._owns_executor = executor is None
        self._executor_shutdown = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._async_transport = AsyncTransport(self, self._master.transport)

    @property
    def sync_master(self) -> Any:
        return self._master

    @property
    def transport(self) -> AsyncTransport:
        return self._async_transport

    @property
    def policy(self) -> Any:
        return self._master.transport.policy

    async def _call(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        async with self._lock:
            loop = asyncio.get_running_loop()
            bound = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(self._executor, bound)

    def _wrap_callable(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def _async_call(*args: Any, **kwargs: Any) -> Any:
            return await self._call(func, *args, **kwargs)

        return _async_call

    def _shutdown_executor(self) -> None:
        if self._owns_executor and not self._executor_shutdown:
            self._executor.shutdown(wait=True)
            self._executor_shutdown = True

    def subscribe_frames(
        self,
        *,
        categories: Iterable[FrameCategory] | None = None,
        maxsize: int = 0,
    ) -> AsyncFrameSubscription:
        return self.transport.subscribe_frames(categories=categories, maxsize=maxsize)

    def subscribe_daq(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.transport.subscribe_daq(maxsize=maxsize)

    def subscribe_events(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.transport.subscribe_events(maxsize=maxsize)

    def subscribe_responses(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.transport.subscribe_responses(maxsize=maxsize)

    def subscribe_services(self, *, maxsize: int = 0) -> AsyncFrameSubscription:
        return self.transport.subscribe_services(maxsize=maxsize)

    async def close(self) -> None:
        if self._closed:
            self._shutdown_executor()
            return
        self._closed = True
        try:
            await self._call(self._master.close)
        finally:
            self._shutdown_executor()

    async def __aenter__(self) -> "AsyncMaster":
        await self._call(self._master.transport.connect)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        if self._closed:
            self._shutdown_executor()
            return None
        self._closed = True
        try:
            return await self._call(self._master.__exit__, exc_type, exc_val, exc_tb)
        finally:
            self._shutdown_executor()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._master, name)
        if callable(attr):
            return self._wrap_callable(attr)
        return attr

    def __dir__(self) -> list[str]:
        return sorted(set(dir(type(self)) + dir(self._master)))
