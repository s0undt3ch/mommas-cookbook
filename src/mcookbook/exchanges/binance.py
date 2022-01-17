"""
Binance exchange implementation.
"""
from __future__ import annotations

from typing import Any

import attrs

from mcookbook.exchanges.abc import Exchange


@attrs.define(kw_only=True, auto_attribs=False)
class BinanceFutures(Exchange):
    """
    Binance futures exchange implementation.
    """

    __exchange_name__: str = "binance"
    __exchange_market__: str = "future"

    @staticmethod
    def get_ccxt_config() -> dict[str, Any]:
        """
        Exchange specific ccxt configuration.

        Return a dictionary with extra options to pass to ccxt when creating the
        connection instance.
        """
        return {"options": {"defaultType": BinanceFutures.__exchange_market__}}
