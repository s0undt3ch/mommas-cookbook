"""
Static pair list handler.
"""
from __future__ import annotations

import copy
from typing import Any

import attrs

from mcookbook.pairlist.abc import PairList


@attrs.define(kw_only=True)
class StaticPairList(PairList):
    """
    Static pair list handler.
    """

    name: str = attrs.field()
    allow_inactive: bool = attrs.field(default=False)

    def gen_pairlist(self, tickers: dict[str, Any]) -> list[str]:
        """
        Generate the pairlist.

        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: List of pairs
        """
        if self.allow_inactive:
            return self.verify_whitelist(self.exchange_config.pair_allow_list, keep_invalid=True)
        else:
            return self._whitelist_for_active_markets(
                self.verify_whitelist(self.exchange_config.pair_allow_list)
            )

    def filter_pairlist(self, pairlist: list[str], tickers: dict[str, Any]) -> list[str]:
        """
        Filters and sorts pairlist and returns the whitelist again.

        Called on each bot iteration - please use internal caching if necessary
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: new whitelist
        """
        pairlist_ = copy.deepcopy(pairlist)
        for pair in self.exchange_config.pair_allow_list:
            if pair not in pairlist_:
                pairlist_.append(pair)
        return pairlist_
