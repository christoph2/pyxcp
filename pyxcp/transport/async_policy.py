#!/usr/bin/env python

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from collections.abc import Iterable

from .transport_ext import FrameCategory


class SubscriptionClosedError(RuntimeError):
    """Raised when reading from a closed async frame subscription."""


@dataclass(frozen=True, slots=True)
class FrameNotification:
    """Transport frame mirrored into an asyncio-friendly representation."""

    category: FrameCategory
    counter: int
    timestamp: int
    payload: bytes


class AsyncFrameSubscription:
    """Async iterator over mirrored transport frames."""

    def __init__(
        self,
        adapter: "AsyncPolicyAdapter",
        *,
        categories: Iterable[FrameCategory] | None = None,
        maxsize: int = 0,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._adapter = adapter
        self._loop = loop or asyncio.get_running_loop()
        self._queue: asyncio.Queue[object] = asyncio.Queue(maxsize=maxsize)
        self._closed = False
        self._sentinel = object()
        self._categories = frozenset(categories) if categories is not None else None

    def matches(self, notification: FrameNotification) -> bool:
        return self._categories is None or notification.category in self._categories

    def publish(self, notification: FrameNotification) -> None:
        def _enqueue() -> None:
            if self._closed or not self.matches(notification):
                return
            try:
                self._queue.put_nowait(notification)
            except asyncio.QueueFull:
                self._adapter.logger.warning(
                    "Async frame subscription queue is full; dropping %s frame.",
                    notification.category.name,
                )

        self._loop.call_soon_threadsafe(_enqueue)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._adapter._unsubscribe(self)

        def _close_queue() -> None:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            self._queue.put_nowait(self._sentinel)

        self._loop.call_soon_threadsafe(_close_queue)

    async def get(self) -> FrameNotification:
        if self._closed and self._queue.empty():
            raise SubscriptionClosedError("Async frame subscription is closed.")
        item = await self._queue.get()
        if item is self._sentinel:
            raise SubscriptionClosedError("Async frame subscription is closed.")
        return item

    def empty(self) -> bool:
        return self._queue.empty()

    def qsize(self) -> int:
        return self._queue.qsize()

    def __aiter__(self) -> "AsyncFrameSubscription":
        return self

    async def __anext__(self) -> FrameNotification:
        try:
            return await self.get()
        except SubscriptionClosedError as exc:
            raise StopAsyncIteration from exc


class AsyncPolicyAdapter:
    """Decorate an existing transport policy with asyncio subscriptions.

    The wrapped policy keeps receiving every frame via ``feed`` so existing
    recorder/DAQ behavior stays intact. In parallel, selected frames are
    mirrored into ``asyncio`` queues through :class:`AsyncFrameSubscription`.
    """

    def __init__(self, delegate: Any = None) -> None:
        self.delegate = delegate
        self.logger = logging.getLogger("pyxcp.async_policy")
        self._subscriptions: set[AsyncFrameSubscription] = set()
        self._finalized = False
        self._xcp_master = getattr(delegate, "xcp_master", None)

    @property
    def xcp_master(self) -> Any:
        return self._xcp_master

    @xcp_master.setter
    def xcp_master(self, value: Any) -> None:
        self._xcp_master = value
        if self.delegate is not None:
            setattr(self.delegate, "xcp_master", value)

    def subscribe(
        self,
        *,
        categories: Iterable[FrameCategory] | None = None,
        maxsize: int = 0,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> AsyncFrameSubscription:
        if self._finalized:
            raise RuntimeError("Cannot subscribe to a finalized async policy.")
        subscription = AsyncFrameSubscription(self, categories=categories, maxsize=maxsize, loop=loop)
        self._subscriptions.add(subscription)
        return subscription

    def subscribe_daq(self, *, maxsize: int = 0, loop: asyncio.AbstractEventLoop | None = None) -> AsyncFrameSubscription:
        return self.subscribe(categories={FrameCategory.DAQ}, maxsize=maxsize, loop=loop)

    def subscribe_events(
        self,
        *,
        maxsize: int = 0,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> AsyncFrameSubscription:
        return self.subscribe(categories={FrameCategory.EVENT}, maxsize=maxsize, loop=loop)

    def subscribe_responses(
        self,
        *,
        maxsize: int = 0,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> AsyncFrameSubscription:
        return self.subscribe(categories={FrameCategory.RESPONSE}, maxsize=maxsize, loop=loop)

    def feed(self, category: FrameCategory, counter: int, timestamp: int, payload: bytes) -> None:
        if self.delegate is not None:
            self.delegate.feed(category, counter, timestamp, payload)

        notification = FrameNotification(
            category=category,
            counter=int(counter),
            timestamp=int(timestamp),
            payload=bytes(payload),
        )
        for subscription in tuple(self._subscriptions):
            subscription.publish(notification)

    def finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        try:
            if self.delegate is not None and hasattr(self.delegate, "finalize"):
                self.delegate.finalize()
        finally:
            for subscription in tuple(self._subscriptions):
                subscription.close()

    def _unsubscribe(self, subscription: AsyncFrameSubscription) -> None:
        self._subscriptions.discard(subscription)

    def __getattr__(self, name: str) -> Any:
        if self.delegate is None:
            raise AttributeError(name)
        return getattr(self.delegate, name)
