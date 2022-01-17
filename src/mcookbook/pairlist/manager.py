"""
Pair list manager.
"""
# pylint: disable=no-member,not-an-iterable,unsubscriptable-object
from __future__ import annotations

import logging
from typing import Any
from typing import TYPE_CHECKING

import attrs
from cachetools import cached
from cachetools import TTLCache
from ccxt.async_support import Exchange as CCXTExchange

from mcookbook.events import Events
from mcookbook.utils.pairlist import expand_pairlist

if TYPE_CHECKING:
    from mcookbook.config.base import BaseConfig
    from mcookbook.pairlist.abc import PairList  # noqa: E402e
    from mcookbook.exchanges.abc import Exchange  # noqa: E402e


log = logging.getLogger(__name__)


@attrs.define(kw_only=True)
class PairListManager:
    """
    Pair list manager.
    """

    config: BaseConfig = attrs.field()
    events: Events = attrs.field()
    ccxt_conn: CCXTExchange = attrs.field()
    exchange: Exchange = attrs.field()

    _allow_list: list[str] = attrs.field(factory=list)
    _block_list: list[str] = attrs.field(factory=list)
    _pairlist_handlers: list[PairList] = attrs.field(factory=list)
    _tickers_needed: bool = attrs.field(default=False)

    def __attrs_post_init__(self) -> None:
        """
        Post attrs, initialization routines.
        """
        self.events.on_start.register(self._populate_internal_config)
        self.events.on_markets_available.register(self._on_markets_available)

    async def _on_markets_available(
        self, *, markets: dict[str, Any]  # pylint: disable=unused-argument
    ) -> None:
        await self.refresh_pairlist()

    async def _populate_internal_config(self) -> None:

        for handler_config in self.config.pairlists:
            self._pairlist_handlers.append(
                handler_config.init_handler(
                    name=handler_config.name,
                    config=handler_config,
                    exchange=self.exchange,
                    ccxt_conn=self.ccxt_conn,
                    pairlist_manager=self,
                )
            )
        for pair in self.config.exchange.pair_allow_list:
            self._allow_list.append(pair)
        for pair in self.config.exchange.pair_block_list:
            self._block_list.append(pair)
        for handler in self._pairlist_handlers:
            self._tickers_needed |= handler.needstickers

    @property
    def expanded_blacklist(self) -> list[str]:
        """
        The expanded blacklist (including wildcard expansion).
        """
        return expand_pairlist(self._block_list, list(self.exchange.markets))

    @cached(TTLCache(maxsize=1, ttl=1800))
    async def _get_cached_tickers(self) -> dict[str, Any]:
        log.info("Fetching tickers for exchange %s", self.config.exchange.name)
        tickers: dict[str, Any] = await self.ccxt_conn.get_tickers()
        return tickers

    async def refresh_pairlist(self) -> None:
        """
        Run pairlist through all configured Pairlist Handlers.
        """
        log.info("Refreshing pairlist...")
        # Tickers should be cached to avoid calling the exchange on each call.
        tickers: dict[str, Any] = {}
        if self._tickers_needed:
            tickers = await self._get_cached_tickers()

        # Generate the pairlist with first Pairlist Handler in the chain
        pairlist = self._pairlist_handlers[0].gen_pairlist(tickers)

        # Process all Pairlist Handlers in the chain
        # except for the first one, which is the generator.
        for pairlist_handler in self._pairlist_handlers[1:]:
            pairlist = pairlist_handler.filter_pairlist(pairlist, tickers)

        # Validation against blacklist happens after the chain of Pairlist Handlers
        # to ensure blacklist is respected.
        pairlist = self.verify_blacklist(pairlist)

        self._allow_list = pairlist
        log.info("Loaded pair list: %s", self._allow_list)

    def verify_blacklist(self, pairlist: list[str]) -> list[str]:
        """
        Verify and remove items from pairlist - returning a filtered pairlist.

        :param pairlist: Pairlist to validate
        :return: pairlist - blacklisted pairs
        """
        try:
            blacklist = self.expanded_blacklist
        except ValueError as err:
            log.error("Pair blacklist contains an invalid Wildcard: %s", err)
            return []
        for pair in pairlist.copy():
            if pair in blacklist:
                log.warning("Pair %s in your blacklist. Removing it from whitelist...", pair)
                pairlist.remove(pair)
        return pairlist

    def verify_whitelist(self, pairlist: list[str], keep_invalid: bool = False) -> list[str]:
        """
        Verify and remove items from pairlist - returning a filtered pairlist.

        :param pairlist: Pairlist to validate
        :param keep_invalid: If sets to True, drops invalid pairs silently while expanding regexes.
        :return: pairlist - whitelisted pairs
        """
        try:

            whitelist = expand_pairlist(pairlist, list(self.exchange.markets), keep_invalid)
        except ValueError as err:
            log.error("Pair whitelist contains an invalid Wildcard: %s", err)
            return []
        return whitelist
