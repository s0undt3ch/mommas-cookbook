"""
Pair list handlers configurations.
"""
from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from mcookbook.pairlist.abc import PairList

PairListConfigType = TypeVar("PairListConfigType", bound="PairListConfig")


class PairListConfig(BaseModel):
    """
    Base pairlist configuration.
    """

    _order: int = PrivateAttr()
    _handler_name: str = PrivateAttr()
    name: str = Field(...)
    refresh_period: int = Field(default=1800, ge=0)

    def __new__(  # pylint: disable=unused-argument
        cls: type[PairListConfig], name: str, **kwargs: Any
    ) -> PairListConfig:
        """
        Override class to instantiate.

        Override __new__ so that we can switch the class with one of it's
        sub-classes before instantiating.
        """
        for subclass in cls.__subclasses__():
            if subclass._handler_name == name:
                return BaseModel.__new__(subclass)
        raise ValueError(f"Cloud not find an {name} pairlist config implementation.")

    def __init_subclass__(cls, *, handler_name: str, **kwargs: Any):
        """
        Post attrs, initialization routines.
        """
        super().__init_subclass__(**kwargs)
        cls._handler_name = handler_name

    def init_handler(self, **kwargs: Any) -> PairList:
        """
        Instantiate the pair list handler corresponding to this configuration.
        """
        from mcookbook.pairlist.abc import PairList  # pylint: disable=import-outside-toplevel

        for subclass in PairList.__subclasses__():
            if subclass.__name__ == self._handler_name:
                return subclass(**kwargs)
        raise ValueError(f"Cloud not find an {self.name} pairlist handler implementation.")


class StaticPairListConfig(PairListConfig, handler_name="StaticPairList"):
    """
    Static pair list configuration.
    """
