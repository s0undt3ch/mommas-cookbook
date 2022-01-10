"""
Internal event pub/sub implementation.
"""
from __future__ import annotations

import abc
import asyncio
import logging
from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

import attrs
from mypy_extensions import NamedArg

log = logging.getLogger(__name__)

AnyCallback = Callable[[Any, Any], Coroutine[Any, Any, None]]
NoArgsCallback = Callable[[None, Any], Coroutine[Any, Any, None]]
NoKwArgsCallback = Callable[[Any, None], Coroutine[Any, Any, None]]
NoArgsNoKwArgsCallback = Callable[[], Coroutine[Any, Any, None]]
MarketsAvailableCallback = Callable[[NamedArg(dict[str, Any], "markets")], Coroutine[Any, Any, Any]]


@attrs.define(kw_only=True)
class Event(abc.ABC):
    """
    Base event class.
    """

    __subscribers__: set[Any]

    def _register(self, func: Any) -> None:
        log.debug("Registering %s on %s", func.__qualname__, self.__class__.__name__)
        self.__subscribers__.add(func)

    def _unregister(self, func: Any) -> None:
        log.debug("Un-registering %s from %s", func.__qualname__, self.__class__.__name__)
        self.__subscribers__.remove(func)

    async def _emit(self, *args: Any, **kwargs: Any) -> None:
        """
        Emit the event.

        Goes through all of the registered functions and calls them with the passed arguments and keyword arguments.
        """
        log.debug("Emitting %s event ...", self.__class__.__name__)
        tasks = []
        for subscriber in self.__subscribers__:
            tasks.append(
                asyncio.create_task(
                    self._emit_wrapper(subscriber, *args, **kwargs),
                ),
            )
        await asyncio.gather(*tasks)
        return None

    async def _emit_wrapper(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            await func(*args, **kwargs)
        except Exception as exc:
            log.exception(
                "Exception raised when calling subscribers of %s(callback: %s): %s",
                self.__class__.__name__,
                func.__qualname__,
                exc,
            )
            raise


@attrs.define(kw_only=True)
class Start(Event):
    """
    Event emitted when the application is starting.
    """

    __subscribers__: set[NoArgsNoKwArgsCallback] = attrs.field(factory=set)

    def register(self, func: NoArgsNoKwArgsCallback) -> None:
        """
        Register a function to be called whenever this event's ``.emit()`` method is called.
        """
        self._register(func)

    def unregister(self, func: NoArgsNoKwArgsCallback) -> None:
        """
        Un-register a previously registered function.
        """
        self._unregister(func)

    async def emit(self) -> None:
        """
        Emit the start event.
        """
        await self._emit()


@attrs.define(kw_only=True)
class Stop(Event):
    """
    Event emitted when the application is stopping.
    """

    __subscribers__: set[NoArgsNoKwArgsCallback] = attrs.field(factory=set)

    def register(self, func: NoArgsNoKwArgsCallback) -> None:
        """
        Register a function to be called whenever this event's ``.emit()`` method is called.
        """
        self._register(func)

    def unregister(self, func: NoArgsNoKwArgsCallback) -> None:
        """
        Un-register a previously registered function.
        """
        self._unregister(func)

    async def emit(self) -> None:
        """
        Emit the stop event.
        """
        await self._emit()


@attrs.define(kw_only=True)
class MarketsAvailable(Event):
    """
    Event emitted when the exchange markets have been loaded.
    """

    __subscribers__: set[MarketsAvailableCallback] = attrs.field(factory=set)

    def register(self, func: MarketsAvailableCallback) -> None:
        """
        Register a function to be called whenever this event's ``.emit()`` method is called.
        """
        self._register(func)

    def unregister(self, func: MarketsAvailableCallback) -> None:
        """
        Un-register a previously registered function.
        """
        self._unregister(func)

    async def emit(self, *, markets: dict[str, Any]) -> None:
        """
        Emit the markets available event.
        """
        await self._emit(markets=markets)


@attrs.define
class Events:
    """
    Application events support.
    """

    _on_stop_event: Stop = attrs.field(factory=Stop)
    _on_start_event: Start = attrs.field(factory=Start)
    _on_markets_available: MarketsAvailable = attrs.field(factory=MarketsAvailable)

    @property
    def on_start(self) -> Start:
        """
        On start event.
        """
        return self._on_start_event

    @property
    def on_stop(self) -> Stop:
        """
        On stop event.
        """
        return self._on_stop_event

    @property
    def on_markets_available(self) -> MarketsAvailable:
        """
        On targets available event.
        """
        return self._on_markets_available