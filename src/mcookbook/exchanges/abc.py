"""
Base exchange class implementation.
"""
# pylint: disable=no-member,not-an-iterable,unsubscriptable-object
from __future__ import annotations

import abc
import logging
from typing import Any
from typing import TYPE_CHECKING

import attrs

from mcookbook.config.trade import TradeConfig
from mcookbook.events import Events
from mcookbook.exceptions import OperationalException
from mcookbook.utils.ccxt import CCXTExchange

log = logging.getLogger(__name__)


if TYPE_CHECKING:
    from mcookbook.config.base import BaseConfig


@attrs.define(kw_only=True, auto_attribs=False)
class Exchange(abc.ABC):
    """
    Base Exchange class.
    """

    __exchange_name__: str
    __exchange_market__: str

    config: TradeConfig = attrs.field()
    events: Events = attrs.field()
    ccxt_conn: CCXTExchange = attrs.field()

    _markets: dict[str, dict[str, Any]] = attrs.field(init=False, repr=False, factory=dict)

    def __attrs_post_init__(self) -> None:
        """
        Post attrs, initialization routines.
        """
        self.events.on_start.register(self._on_start)

    async def _on_start(self) -> None:
        await self.get_markets()

    @staticmethod
    def get_ccxt_headers() -> dict[str, str]:
        """
        Return exchange specific HTTP headers dictionary.

        Return a dictionary with extra HTTP headers to pass to ccxt when creating the
        connection instance.
        """
        return {}

    @staticmethod
    def get_ccxt_config() -> dict[str, Any]:
        """
        Return exchange specific configuration dictionary.

        Return a dictionary with extra options to pass to ccxt when creating the
        connection instance.
        """
        return {}

    @classmethod
    def resolve_class(cls, config: BaseConfig) -> type[Exchange]:
        """
        Resolve the exchange class to use based on the configuration.
        """
        name = config.exchange.name
        market = config.exchange.market
        for subclass in cls.__subclasses__():
            subclass_name = subclass.__exchange_name__
            subclass_market = subclass.__exchange_market__
            if subclass_name == name and market == subclass_market:
                return subclass
        raise OperationalException(
            f"Could not properly resolve the exchange class based on exchange name {name!r} and market {market!r}."
        )

    async def get_markets(self) -> dict[str, Any]:
        """
        Load the exchange markets.
        """
        if not self._markets:
            log.info("Loading markets")
            self._markets = await self.ccxt_conn.load_markets()
            await self.events.on_markets_available.emit(markets=self._markets)
        return self._markets

    @property
    def markets(self) -> dict[str, Any]:
        """
        Return the loaded markets.
        """
        return self._markets
