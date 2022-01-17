"""
Base configuration schemas.
"""
from __future__ import annotations

import json
import pathlib
import pprint
import traceback
from typing import Any
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field
from pydantic import PrivateAttr
from pydantic import validator

from mcookbook.config.exchange import ExchangeConfig
from mcookbook.config.logging import LoggingConfig
from mcookbook.config.pairlist import PairListConfig
from mcookbook.exceptions import MCookBookSystemExit
from mcookbook.utils.dicts import merge_dictionaries
from mcookbook.utils.dicts import sanitize_dictionary

BaseConfigType = TypeVar("BaseConfigType", bound="BaseConfig")


class BaseConfig(BaseModel):
    """
    Base configuration model.
    """

    class Config:
        """
        Schema configuration.
        """

        extra = "forbid"
        allow_mutation = False
        validate_assignment = True

    exchange: ExchangeConfig = Field(..., allow_mutation=False)
    pairlists: list[PairListConfig] = Field(min_items=1)
    pairlist_refresh_period: int = 3600

    # Optional Configs
    logging: LoggingConfig = LoggingConfig()

    # Private attributes
    _basedir: pathlib.Path = PrivateAttr()

    @classmethod
    def parse_files(cls: type[BaseConfigType], *files: pathlib.Path | str) -> BaseConfigType:
        """
        Helper class method to load the configuration from multiple files.
        """
        if not files:
            raise ValueError("No configuration files were passed")
        config_dicts: list[dict[str, Any]] = []
        for file in files:
            if not isinstance(file, pathlib.Path):
                file = pathlib.Path(file)
            config_dicts.append(json.loads(file.read_text(encoding="utf-8")))
        config = config_dicts.pop(0)
        if config_dicts:
            merge_dictionaries(config, *config_dicts)
        cls.update_forward_refs()
        try:
            return cls(**config)
        except Exception as exc:
            raise MCookBookSystemExit(
                f"Failed to load configuration files:\n{traceback.format_exc()}\n\n"
                "Merged dictionary:\n"
                f'{pprint.pformat(sanitize_dictionary(config, ("key", "secret", "password", "uid")))}'
            ) from exc

    @validator("pairlists")
    @classmethod
    def _set_pairlist_position(cls, value: list[PairListConfig]) -> list[PairListConfig]:
        for idx, pairlist in enumerate(value):
            pairlist._order = idx
        return value

    @property
    def basedir(self) -> pathlib.Path:
        """
        Return the base directory.
        """
        return self._basedir
